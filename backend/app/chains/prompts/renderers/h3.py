"""MiniMax H3 官方提示词格式渲染器。

依据 H3 官方提示词规范（`h3-prompt-writing` skill，`references/ref-en.txt` 与
`references/base-en.txt`）：

- **全参考模式**（有参考素材）用固定六段：
  `subject_definitions` → `summary` → `retention_analysis` → `detailed_description`
  → `overall_soundscape` → `non_diegetic_music`；
- **基础模式**（首帧/尾帧/纯文本）用三段：
  `integrated_multimodal_description` → `overall_soundscape` → `non_diegetic_music`；
- 首帧/尾帧/首尾帧模式必须在正文前写官方对齐句；
- 正文为英文；仅 `<d>` 内的台词/歌词与画面可见文字保留原语言；
- 参考模式要求先在 `[Shot 1]` 之前用 1–2 句英文确立风格；
- `[Shot 1]` 不带时间戳，后续镜头写 `[Shot N] At MM:SS.mmm, ...`；
- 说话人用稳定 `(S1)`/`(S2)`；台词写 `<d>[Language] ...</d>`；
- 音频参考写 `<Audio N> is the voice-timbre reference for <Subject N> (S1).`。

渲染器是**确定性拼装 + 校验**：正文英文由上游 LLM 提供（`H3Prose`），
未提供时输出结构化骨架并给出警告，便于预览与排障。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field

from app.chains.prompts.ir import IRPrompt, IRShot

# 与优云智算 ModelVerse H3 通道一致的上限（`MAX_PROMPT_CHARS`）。
H3_MAX_PROMPT_CHARS = 7000
# 生成类任务的建议英文词数区间（官方口径；短镜头按自适应区间校验）。
H3_RECOMMENDED_WORD_RANGE = (350, 500)

REFERENCE_SECTION_ORDER: tuple[str, ...] = (
    "subject_definitions",
    "summary",
    "retention_analysis",
    "detailed_description",
    "overall_soundscape",
    "non_diegetic_music",
)

BASE_SECTION_ORDER: tuple[str, ...] = (
    "integrated_multimodal_description",
    "overall_soundscape",
    "non_diegetic_music",
)

KNOWN_TASK_TYPES: tuple[str, ...] = (
    "keyframe completion",
    "reference generation",
    "video editing",
    "video continuation",
    "audio reuse",
    "audio reference",
)

# 可见内容保留标记。
VISIBLE_RETENTION_MARKERS: tuple[str, ...] = (
    "fully_preserved",
    "partially_preserved",
    "attribute_transfer",
    "weak_reference",
)

# 音频保留标记。
AUDIO_RETENTION_MARKERS: tuple[str, ...] = (
    "fully_copy",
    "partially_copy",
    "reference",
    "weak_reference",
)

# 参考模式与基础模式的输入模式集合。
REFERENCE_MODE = "reference"
BASE_MODES = {"first", "last", "key", "first_last", "first_last_key", "text_only"}

_TIMESTAMP_PATTERN = re.compile(r"At (\d{2,}:\d{2}\.\d{3})")
_LABEL_DEFINITION_PATTERN = re.compile(
    r"^<(Subject|Picture|Video|Audio) (\d+)>(?:\s+is\b|\s*:)", re.MULTILINE
)
_LABEL_USAGE_PATTERN = re.compile(r"<(Subject|Picture|Video|Audio) (\d+)>")
_AUDIO_RETENTION_PATTERN = re.compile(
    r"^<Audio (\d+)>[^\n]*?:\s*(fully_copy|partially_copy|reference|weak_reference)\b",
    re.MULTILINE,
)
_SUBJECT_RETENTION_PATTERN = re.compile(
    r"^<Subject (\d+)>[^\n]*?:\s*(fully_preserved|partially_preserved|attribute_transfer|weak_reference)\b",
    re.MULTILINE,
)


class H3Prose(BaseModel):
    """由上游 LLM 提供的英文正文分段落。

    每个字段对应 H3 的一个段落正文（不含段落名本身）。为空时该段落回落到结构化骨架。
    """

    model_config = ConfigDict(extra="forbid")

    subject_definitions: str = Field("", description="subject_definitions 段落正文")
    summary: str = Field("", description="summary 段落正文")
    retention_analysis: str = Field("", description="retention_analysis 段落正文")
    detailed_description: str = Field("", description="detailed_description 段落正文")
    overall_soundscape: str = Field("", description="overall_soundscape 段落正文")
    non_diegetic_music: str = Field("", description="non_diegetic_music 段落正文")
    integrated_multimodal_description: str = Field("", description="基础模式主段落正文")


@dataclass
class H3RenderResult:
    """渲染结果。"""

    text: str
    warnings: list[str] = field(default_factory=list)
    char_count: int = 0
    word_count: int = 0


def format_timestamp(seconds: float) -> str:
    """把秒数格式化为 H3 要求的 `MM:SS.mmm`（超过 59 分钟时分钟位自然增长）。"""
    total_ms = int(round(max(0.0, float(seconds or 0.0)) * 1000))
    minutes, remainder = divmod(total_ms, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{minutes:02d}:{secs:02d}.{millis:03d}"


def format_seconds(seconds: float) -> str:
    """对齐句要求 `S.SS`（两位小数），与 `MM:SS.mmm` 是两套格式。"""
    return f"{max(0.0, float(seconds or 0.0)):.2f}"


def _trim_sentence(text: str) -> str:
    """去掉句末重复标点，便于拼装 `Sound:` / `Continuity:` 前缀。"""
    return str(text or "").strip().rstrip("。.!！?？")


def word_range_for_duration(duration_seconds: float | None) -> tuple[int, int]:
    """按镜头时长给出 H3 英文正文的建议词数区间。

    官方建议生成类任务 350–500 词，但 5 秒短剧单镜头达不到该体量；
    这里按时长自适应，避免把「写短」误判成不合格。
    """
    seconds = max(0.0, float(duration_seconds or 0.0))
    if seconds <= 6.0:
        return (200, 300)
    if seconds <= 10.0:
        return (300, 400)
    return H3_RECOMMENDED_WORD_RANGE


def _parse_timestamp(value: str) -> float:
    minutes, rest = value.split(":")
    secs, millis = rest.split(".")
    return int(minutes) * 60 + int(secs) + int(millis) / 1000.0


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _count_words(text: str) -> int:
    return len([token for token in str(text or "").split() if token.strip()])


def _section_body(text: str, name: str) -> str:
    """取出 `name:` 所在段落的正文（截到下一个段落名之前）。"""
    marker = f"{name}:"
    start = str(text or "").find(marker)
    if start < 0:
        return ""
    start += len(marker)
    end = len(text)
    for other in REFERENCE_SECTION_ORDER + BASE_SECTION_ORDER:
        if other == name:
            continue
        position = text.find(f"{other}:", start)
        if position >= 0:
            end = min(end, position)
    return text[start:end]


def h3_label_for(kind: str, subject_index: int, picture_index: int) -> str:
    """把内部参考类型映射为 H3 标签。

    参考素材用于**定义内容单元**（角色/场景/道具/服装/风格）时用 `<Subject N>`；
    只有作为**具体目标帧或分镜锚点**时才用 `<Picture N>`。
    """
    if str(kind or "") == "frame":
        return f"<Picture {picture_index}>"
    return f"<Subject {subject_index}>"


def build_h3_alignment_instruction(ir: IRPrompt, *, reference_mode: str | None = None) -> str:
    """生成首帧/尾帧/首尾帧的官方对齐句。

    - I2VA / 单关键帧：`<Picture 1>` 对齐 0.00 秒；
    - L2VA：`<Picture 1>` 对齐总时长；
    - FL2VA：`<Picture 1>` 对齐 0.00 秒，`Picture 2` 对齐总时长。
    """
    mode = str(reference_mode or ir.reference_mode or "").strip().lower()
    duration = format_seconds(ir.duration_seconds)
    if mode in {"first", "key"}:
        return (
            "For the target video, at 0.00 seconds into the target video, "
            "<Picture 1> (from [Shot 1]) is fully referenced."
        )
    if mode in {"first_last", "first_last_key"}:
        return (
            "How the reference pictures align with the target video — "
            "Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; "
            f"Picture 2 (from Shot 1) aligns with the {duration}-second mark of the target video."
        )
    if mode == "last":
        return (
            "How the reference pictures align with the target video — "
            f"<Picture 1> (from [Shot 1]) aligns with the {duration}-second mark of the target video."
        )
    return ""


# --------------------------------------------------------------------------- #
# 骨架回落（无 LLM 英文正文时）
# --------------------------------------------------------------------------- #


_CJK_RE = re.compile(r"[\u3400-\u9fff]")
_SHOT_SIZE_LABELS = {
    "ECU": "extreme close-up",
    "CU": "close-up",
    "MCU": "medium close-up",
    "MS": "medium shot",
    "MLS": "medium-wide shot",
    "LS": "wide shot",
    "ELS": "extreme wide shot",
}
_CAMERA_ANGLE_LABELS = {
    "EYE_LEVEL": "eye-level angle",
    "HIGH_ANGLE": "high angle",
    "LOW_ANGLE": "low angle",
    "OVERHEAD": "overhead angle",
    "DUTCH_ANGLE": "dutch angle",
}
_CAMERA_MOVEMENT_LABELS = {
    "STATIC": "static camera",
    "PAN": "pan",
    "TILT": "tilt",
    "DOLLY": "dolly",
    "TRACK": "tracking camera",
    "ZOOM": "zoom",
    "HANDHELD": "handheld camera",
}
_SUBJECT_KIND_NOUNS = {
    "character": "character",
    "scene": "environment",
    "prop": "prop",
    "costume": "costume",
    "frame": "frame",
}


def _has_cjk(text: str) -> bool:
    """判断文本是否包含中文；H3 正文除台词/专有名词外必须为英文。"""
    return bool(_CJK_RE.search(str(text or "")))


def _english_or_empty(text: str) -> str:
    """保留英文文本；中文自由描述不回落到 H3 正文，避免被模型朗读成旁白。"""
    value = str(text or "").strip()
    return "" if _has_cjk(value) else value


def _subject_labels(shot: IRShot) -> list[str]:
    """把 IRShot.subjects 的 `Subject N` 转成 `<Subject N>` 标签。"""
    labels: list[str] = []
    for item in shot.subjects:
        value = str(item or "").strip()
        if not value:
            continue
        labels.append(value if value.startswith("<") else f"<{value}>")
    return labels


def _style_sentence(ir: IRPrompt) -> str:
    bits: list[str] = ["The target video uses a consistent short-drama visual style."]
    style_anchor = _english_or_empty(ir.style_anchor)
    if style_anchor:
        bits.append(f"Visual style anchor: {style_anchor}.")
    if ir.aspect_ratio:
        bits.append(f"The frame is composed for delivery at {ir.aspect_ratio}.")
    if ir.duration_seconds:
        bits.append(f"Total duration is {ir.duration_seconds:g} seconds.")
    bits.append(
        "Subject identity, clothing, environment, spatial layout, and lighting direction "
        "remain consistent with the supplied references throughout the shot."
    )
    return " ".join(bits)


def _subject_label_for_speaker(ir: IRPrompt, speaker_id: str) -> str:
    for subject in ir.subjects:
        if subject.speaker_id and subject.speaker_id == speaker_id:
            return subject.label
    return ""


def _subject_for_speaker(ir: IRPrompt, speaker_id: str):
    for subject in ir.subjects:
        if subject.speaker_id and subject.speaker_id == speaker_id:
            return subject
    return None


def _dialogue_fragment(ir: IRPrompt, line, *, use_labels: bool = True) -> str:
    """把一条台词写成 H3 正文片段，按 line_mode 区分口型与声音来源。"""
    language = line.language or "Chinese"
    label = _subject_label_for_speaker(ir, line.speaker_id) if use_labels else ""
    if use_labels and label:
        who = f"<{label}> ({line.speaker_id})"
    else:
        who = f"{line.speaker_name or 'The speaker'} ({line.speaker_id})"

    audio = f" in the voice timbre referenced from <{line.audio_label}>" if line.audio_label else ""
    voice_text = str(getattr(line, "voice_description", "") or "").strip().rstrip("。.!！")
    voice = f", using this voice profile: {voice_text}," if voice_text else ""
    mode = str(line.line_mode or "DIALOGUE").strip().upper()
    if mode == "VOICE_OVER":
        return (
            f"{who}{audio}{voice} says in an off-screen voiceover, "
            f"<d>[{language}] {line.text}</d> while their lips remain completely closed."
        )
    if mode == "OFF_SCREEN":
        return f"{who}{audio}{voice} says off-screen, <d>[{language}] {line.text}</d>."
    if mode == "PHONE":
        return f"{who}{audio}{voice} says through a phone speaker, <d>[{language}] {line.text}</d>."
    return f"{who}{audio}{voice} says, <d>[{language}] {line.text}</d>"


def _token_to_picture_label(token: str) -> str:
    """把内部参考 token（`图1`）转成 H3 的图片标签（`<Picture 1>`）。

    H3 规范：`<Picture N>` 只标识来源、不单独成行时，就写在该 `<Subject N>` 的定义行里。
    """
    match = re.search(r"(\d+)", str(token or ""))
    return f"<Picture {match.group(1)}>" if match else str(token or "").strip()


def _fallback_audio_definitions(ir: IRPrompt) -> list[str]:
    """生成 `<Audio N>` 定义行；没有音频参考时返回空列表。"""
    lines: list[str] = []
    for audio in ir.audio_references:
        subject = _subject_for_speaker(ir, audio.speaker_id)
        if subject is not None:
            target = f"<{subject.label}> ({audio.speaker_id})"
        else:
            target = f"the speaker {audio.speaker_name or ''} ({audio.speaker_id})".replace("  ", " ")
        lines.append(f"<{audio.label}> is the voice-timbre reference for {target.strip()}.")
    return lines


def _fallback_subject_definitions(ir: IRPrompt) -> str:
    lines: list[str] = []
    for subject in ir.subjects:
        source = ""
        if subject.source_tokens:
            sources = ", ".join(_token_to_picture_label(token) for token in subject.source_tokens)
            source = f" in {sources}"
        noun = _SUBJECT_KIND_NOUNS.get(str(subject.kind), "referenced subject")
        text = f"<{subject.label}> is the {noun} {subject.name}{source}"
        definition = _english_or_empty(str(subject.definition or ""))
        if definition:
            text = f"{text}, {definition}"
        lines.append(text.rstrip("。.") + ".")
    lines.extend(_fallback_audio_definitions(ir))
    if not lines:
        return "N/A"
    return "\n".join(lines)


def _fallback_summary(ir: IRPrompt) -> str:
    prefix = " + ".join([t for t in ir.task_types if t in KNOWN_TASK_TYPES]) or "reference generation"
    labels = [f"<{subject.label}>" for subject in ir.subjects]
    subjects = ", ".join(labels) if labels else "the referenced subjects"
    audio = ""
    if ir.audio_references:
        audio = " The voice timbre is referenced from " + ", ".join(
            f"<{item.label}>" for item in ir.audio_references
        ) + "."
    return (
        f"[{prefix}] The target video presents {subjects} in one continuous shot "
        f"with consistent identity and environment.{audio}"
    )


def _fallback_retention_analysis(ir: IRPrompt) -> str:
    lines: list[str] = []
    for subject in ir.subjects:
        appears = ", ".join(f"[Shot {index}]" for index in (subject.appears_in or [1]))
        marker = subject.retention if subject.retention in VISIBLE_RETENTION_MARKERS else "fully_preserved"
        source = ", ".join(
            _token_to_picture_label(token) for token in subject.source_tokens
        )
        suffix = f" from {source}" if source else ""
        noun = _SUBJECT_KIND_NOUNS.get(str(subject.kind), "subject")
        lines.append(
            f"<{subject.label}> (appears in {appears}): {marker} - "
            f"the referenced {noun} is reused as the source of this content unit{suffix}."
        )
    for audio in ir.audio_references:
        subject = _subject_for_speaker(ir, audio.speaker_id)
        target = f"<{subject.label}>" if subject is not None else "the target speaker"
        lines.append(
            f"<{audio.label}>: reference - its vocal timbre guides the dialogue delivery of "
            f"{target} without copying the original signal."
        )
    return "\n".join(lines) if lines else "N/A"


def _fallback_shot_block(ir: IRPrompt, shot: IRShot, *, use_labels: bool = True) -> str:
    if shot.index > 1 and shot.start_seconds > 0:
        header = f"[Shot {shot.index}] At {format_timestamp(shot.start_seconds)},"
    else:
        header = f"[Shot {shot.index}]"

    parts: list[str] = []
    visual = _english_or_empty(shot.visual)
    if visual:
        parts.append(visual.rstrip("。.") + ".")
    elif use_labels and _subject_labels(shot):
        parts.append(
            "The shot presents "
            + ", ".join(_subject_labels(shot))
            + " in one continuous composition."
        )
    else:
        parts.append("The shot presents one continuous composition.")

    size = _SHOT_SIZE_LABELS.get(str(shot.shot_size or "").upper(), "shot")
    angle = _CAMERA_ANGLE_LABELS.get(str(shot.camera_angle or "").upper(), "eye-level angle")
    movement = _CAMERA_MOVEMENT_LABELS.get(
        str(shot.camera_movement or "").upper(), "static camera"
    )
    parts.append(f"{size.capitalize()} at {angle}, {movement}.")

    beats = [item for item in shot.action_beats if _english_or_empty(item)]
    if beats:
        parts.append("Action beats: " + "; ".join(beats).rstrip("。.") + ".")
    elif shot.dialogues:
        parts.append("The speaking character delivers the line while the others remain silent.")
    else:
        parts.append("The subject performs one continuous action within the same space.")

    if _english_or_empty(shot.atmosphere):
        parts.append(f"Atmosphere: {_english_or_empty(shot.atmosphere)}.")
    if _english_or_empty(shot.composition_anchor):
        parts.append(f"Framing: {_english_or_empty(shot.composition_anchor)}.")
    if _english_or_empty(shot.screen_direction):
        parts.append(f"Screen direction: {_english_or_empty(shot.screen_direction)}.")
    for line in shot.dialogues:
        parts.append(_dialogue_fragment(ir, line, use_labels=use_labels))
    if shot.dialogues:
        parts.append(
            "Characters who are not speaking keep their mouths closed and only react physically."
        )
        parts.append(_NO_NARRATION_INSTRUCTION)
    if shot.sound:
        sound = _english_or_empty(shot.sound)
        parts.append(f"Sound: {_trim_sentence(sound or 'Natural room tone and physical sounds continue')}.")
    if shot.continuity:
        parts.append(f"Continuity: {_trim_sentence(shot.continuity)}.")

    body = " ".join(part for part in parts if part).strip()
    return f"{header} {body}".strip() if body else header


def _fallback_detailed_description(ir: IRPrompt) -> str:
    blocks: list[str] = [_style_sentence(ir)]
    for shot in ir.shots:
        blocks.append(_fallback_shot_block(ir, shot, use_labels=True))
    if not ir.shots:
        blocks.append("[Shot 1]")
    return "\n".join(block for block in blocks if str(block).strip())


def _fallback_soundscape(ir: IRPrompt) -> str:
    for shot in ir.shots:
        sound = _english_or_empty(str(shot.sound or ""))
        if sound:
            return sound
    return "Room tone and natural physical sounds continue throughout the video."


def _fallback_music() -> str:
    return "N/A"


def _fallback_multimodal(ir: IRPrompt) -> str:
    """基础模式主段落：不使用全参考标签，只写可见内容与台词。"""
    blocks: list[str] = [_style_sentence(ir)]
    if ir.subjects:
        blocks.append(
            "The referenced subject identity, clothing, environment, and lighting "
            "remain consistent throughout the shot."
        )
    for shot in ir.shots:
        blocks.append(_fallback_shot_block(ir, shot, use_labels=False))
    if not ir.shots:
        blocks.append("[Shot 1]")
    return "\n".join(block for block in blocks if str(block).strip())


_FALLBACK_BUILDERS = {
    "subject_definitions": _fallback_subject_definitions,
    "summary": _fallback_summary,
    "retention_analysis": _fallback_retention_analysis,
    "detailed_description": _fallback_detailed_description,
    "overall_soundscape": _fallback_soundscape,
    "non_diegetic_music": lambda _ir: _fallback_music(),
    "integrated_multimodal_description": _fallback_multimodal,
}


_SILENCE_INSTRUCTION = (
    "No spoken dialogue; characters do not speak and their mouths remain closed."
)
_NO_NARRATION_INSTRUCTION = (
    "Only the dialogue lines are spoken; do not read the shot description, subject definitions, "
    "summary, retention analysis, or continuity text aloud. No narration or voiceover."
)
_CONTINUITY_RE = re.compile(
    r"continuous|one continuous scene|same scene|no cut|background.{0,12}(consistent|same)"
    r"|不切|同一(个)?场景|场景.{0,6}(一致|保持)|连续镜头",
    re.IGNORECASE,
)
_SILENCE_RE = re.compile(
    r"no spoken dialogue|characters do not speak|do not speak|silent|不说话|无对白",
    re.IGNORECASE,
)


def _append_missing_shot_constraints(section_name: str, body: str, ir: IRPrompt) -> str:
    """把声音与连续性硬约束补进 LLM 正文，避免自由改写时丢失关键输入。

    LLM 负责文风，但不能决定是否保留说话人、声音描述、无对白和同一场景约束。
    这里只补缺失项，不重写已有句子，因此不会破坏用户/LLM 已写好的镜头语言。
    """
    if section_name not in {"detailed_description", "integrated_multimodal_description"}:
        return body
    use_labels = section_name == "detailed_description"
    text = str(body or "").strip()
    additions: list[str] = []
    for shot in ir.shots:
        if shot.dialogues:
            for line in shot.dialogues:
                if line.text and line.text not in text:
                    additions.append(_dialogue_fragment(ir, line, use_labels=use_labels))
            voice_profiles: dict[str, str] = {}
            for line in shot.dialogues:
                voice = str(line.voice_description or "").strip().rstrip("。.!！")
                if not voice:
                    continue
                who = line.speaker_name or line.speaker_id
                if voice not in text:
                    voice_profiles[who] = voice
            for who, voice in voice_profiles.items():
                additions.append(f"{who} uses this voice profile: {voice}.")
            if not re.search(
                r"silent|not speaking|mouths? (remain )?closed|保持沉默|不出声",
                text,
                re.IGNORECASE,
            ):
                additions.append(
                    "Characters who are not speaking keep their mouths closed and only react physically."
                )
            if not re.search(
                r"only the dialogue lines are spoken|do not read .*aloud|no narration|no voiceover",
                text,
                re.IGNORECASE,
            ):
                additions.append(_NO_NARRATION_INSTRUCTION)
        elif not _SILENCE_RE.search(text):
            additions.append(_SILENCE_INSTRUCTION)
        if shot.continuity and not _CONTINUITY_RE.search(text):
            additions.append(f"Continuity: {_trim_sentence(shot.continuity)}.")
        if shot.sound and not shot.dialogues and shot.sound not in text:
            additions.append(f"Sound: {_trim_sentence(shot.sound)}.")
    return " ".join([text, *additions]).strip() if additions else text


def _append_missing_audio_lines(section_name: str, body: str, ir: IRPrompt) -> str:
    """LLM 漏写音频定义/留存分析/关键约束时补上骨架行，避免结构不完整。"""
    text = str(body or "").strip()
    if ir.audio_references:
        if section_name == "subject_definitions":
            missing = [line for line in _fallback_audio_definitions(ir) if line.split(" is ")[0] not in text]
            if missing:
                text = "\n".join([text, *missing]).strip()
        elif section_name == "retention_analysis":
            missing: list[str] = []
            for audio in ir.audio_references:
                if f"<{audio.label}>" in text:
                    continue
                missing.append(
                    f"<{audio.label}>: reference - its vocal timbre guides the target speaker's "
                    "dialogue delivery without copying the original signal."
                )
            if missing:
                text = "\n".join([text, *missing]).strip()
    if section_name == "overall_soundscape" and ir.shots and not ir.shots[0].dialogues:
        if not _SILENCE_RE.search(text):
            text = f"{text} {_SILENCE_INSTRUCTION}".strip()
    return _append_missing_shot_constraints(section_name, text, ir)


def _resolve_section(name: str, ir: IRPrompt, prose: H3Prose | None) -> str:
    if prose is not None:
        value = str(getattr(prose, name, "") or "").strip()
        if value:
            return _append_missing_audio_lines(name, value, ir)
    builder = _FALLBACK_BUILDERS.get(name)
    return builder(ir) if builder else ""


# --------------------------------------------------------------------------- #
# 渲染
# --------------------------------------------------------------------------- #


def render_h3_reference(
    ir: IRPrompt,
    *,
    prose: H3Prose | None = None,
    max_chars: int = H3_MAX_PROMPT_CHARS,
) -> H3RenderResult:
    """按 H3 全参考模式渲染六段式提示词。"""
    warnings: list[str] = []
    if prose is None or not any(
        str(getattr(prose, name, "") or "").strip() for name in REFERENCE_SECTION_ORDER
    ):
        warnings.append("未提供英文正文（H3Prose），已输出结构化骨架：结构与标签合规，但正文语言与 IR 一致；H3 可能把非 <d> 文本朗读成旁白，建议配置文本模型或提供英文高级提示词")

    sections: list[str] = []
    for name in REFERENCE_SECTION_ORDER:
        body = _resolve_section(name, ir, prose).strip() or "N/A"
        sections.append(f"{name}:\n{body}")
    text = "\n\n".join(sections).strip()
    if len(ir.shots) == 1:
        description_body = _section_body(text, "detailed_description")
        if re.search(r"\[Shot [2-9]\d*\]", description_body):
            warnings.append("单个业务 Shot 的 H3 正文出现了 [Shot 2+]；默认应保持一个连续镜头")

    warnings.extend(
        validate_h3_reference(text, duration_seconds=ir.duration_seconds, max_chars=max_chars)
    )
    return H3RenderResult(
        text=text,
        warnings=_dedupe(warnings),
        char_count=len(text),
        word_count=_count_words(text),
    )


def render_h3_base(
    ir: IRPrompt,
    *,
    prose: H3Prose | None = None,
    reference_mode: str | None = None,
    max_chars: int = H3_MAX_PROMPT_CHARS,
) -> H3RenderResult:
    """按 H3 基础模式渲染三段式提示词（首帧/尾帧/纯文本）。"""
    warnings: list[str] = []
    mode = str(reference_mode or ir.reference_mode or "text_only").strip().lower()
    if mode == "first_last_key":
        warnings.append("H3 只接收首帧与尾帧；关键帧不会上传，提示词不应把它写成画面锚点")

    if prose is None or not str(getattr(prose, "integrated_multimodal_description", "") or "").strip():
        warnings.append("未提供英文正文（H3Prose），已输出结构化骨架：结构与标签合规，但正文语言与 IR 一致；H3 可能把非 <d> 文本朗读成旁白，建议配置文本模型或提供英文高级提示词")

    sections: list[str] = []
    for name in BASE_SECTION_ORDER:
        body = _resolve_section(name, ir, prose).strip() or "N/A"
        sections.append(f"{name}:\n{body}")
    text = "\n\n".join(sections).strip()
    if len(ir.shots) == 1:
        description_body = _section_body(text, "integrated_multimodal_description")
        if re.search(r"\[Shot [2-9]\d*\]", description_body):
            warnings.append("单个业务 Shot 的 H3 正文出现了 [Shot 2+]；默认应保持一个连续镜头")

    alignment = build_h3_alignment_instruction(ir, reference_mode=mode)
    if alignment:
        text = f"{alignment}\n\n{text}"
    elif mode in {"first", "last", "key", "first_last", "first_last_key"}:
        warnings.append(f"{mode} 模式缺少可用的图片槽位，无法生成官方对齐句")

    warnings.extend(
        validate_h3_base(
            text,
            reference_mode=mode,
            duration_seconds=ir.duration_seconds,
            max_chars=max_chars,
        )
    )
    return H3RenderResult(
        text=text,
        warnings=_dedupe(warnings),
        char_count=len(text),
        word_count=_count_words(text),
    )


def render_h3(
    ir: IRPrompt,
    *,
    prose: H3Prose | None = None,
    reference_mode: str | None = None,
    max_chars: int = H3_MAX_PROMPT_CHARS,
) -> H3RenderResult:
    """按输入模式选择 H3 参考六段或基础三段。

    `reference_mode` 显式传入时以它为准；未传时使用 IR 上的模式。
    兼容旧调用：IR 声明 reference 但没有任何参考图时回落到基础三段。
    """
    mode = str(reference_mode or ir.reference_mode or "reference").strip().lower()
    if reference_mode is None and mode == "reference" and not ir.references:
        mode = "text_only"
    if mode == "reference":
        return render_h3_reference(ir, prose=prose, max_chars=max_chars)
    return render_h3_base(ir, prose=prose, reference_mode=mode, max_chars=max_chars)


# --------------------------------------------------------------------------- #
# 校验
# --------------------------------------------------------------------------- #


def validate_h3_reference(
    text: str,
    *,
    duration_seconds: float | None = None,
    max_chars: int = H3_MAX_PROMPT_CHARS,
) -> list[str]:
    """校验参考模式提示词的结构合规性，返回问题列表（空表示通过）。"""
    warnings: list[str] = []
    body = str(text or "")

    missing = [name for name in REFERENCE_SECTION_ORDER if f"{name}:" not in body]
    if missing:
        warnings.append("缺少 H3 必需段落：" + "、".join(missing))

    positions = [body.find(f"{name}:") for name in REFERENCE_SECTION_ORDER]
    present = [position for position in positions if position >= 0]
    if present != sorted(present):
        warnings.append("H3 段落顺序不符合规范（应为 " + " → ".join(REFERENCE_SECTION_ORDER) + "）")

    # retention_analysis 里也会合法出现 `([Shot 1])`，所以镜头锚点必须在
    # detailed_description 这一段内部查找，不能全文搜索。
    description_body = _section_body(body, "detailed_description")
    summary_body = _section_body(body, "summary").strip()
    if summary_body and not re.match(r"^\[[^\]]+\]", summary_body):
        warnings.append("summary 缺少方括号任务类型前缀（如 [reference generation]）")

    if "[Shot 1]" not in description_body:
        warnings.append("detailed_description 缺少 [Shot 1]")

    shot_one = description_body.find("[Shot 1]")
    if shot_one >= 0 and not description_body[:shot_one].strip():
        warnings.append("参考模式要求在 [Shot 1] 之前先用 1–2 句英文确立风格")

    if re.search(r"\[Shot 1\]\s*At ", description_body):
        warnings.append("[Shot 1] 不应带时间戳（首个镜头不写 At MM:SS.mmm）")

    d_open, d_close = body.count("<d>"), body.count("</d>")
    if d_open != d_close:
        warnings.append(f"<d> 台词标签未成对闭合（{d_open} 开 / {d_close} 闭）")

    # 只有 <Subject N> 必须单行定义；<Picture N>/<Video N>/<Audio N> 按规范写在各定义行内。
    defined_subjects = {
        number for kind, number in _LABEL_DEFINITION_PATTERN.findall(body) if kind == "Subject"
    }
    used_subjects = {
        number for kind, number in _LABEL_USAGE_PATTERN.findall(body) if kind == "Subject"
    }
    undefined = used_subjects - defined_subjects
    if undefined:
        warnings.append(
            "使用了未在 subject_definitions 单行定义的 <Subject N>："
            + "、".join(f"<Subject {number}>" for number in sorted(undefined))
        )

    defined_audio = {
        number for kind, number in _LABEL_DEFINITION_PATTERN.findall(body) if kind == "Audio"
    }
    used_audio = {
        number for kind, number in _LABEL_USAGE_PATTERN.findall(body) if kind == "Audio"
    }
    undefined_audio = used_audio - defined_audio
    if undefined_audio:
        warnings.append(
            "使用了未定义的 <Audio N>："
            + "、".join(f"<Audio {number}>" for number in sorted(undefined_audio))
        )
    if defined_audio and not any(
        f"<Audio {number}>" in description_body for number in defined_audio
    ):
        warnings.append(
            "detailed_description 未引用已定义的 <Audio N>；音色参考应在对应台词前写明"
        )

    for number, marker in _SUBJECT_RETENTION_PATTERN.findall(body):
        if marker not in VISIBLE_RETENTION_MARKERS:
            warnings.append(f"<Subject {number}> 使用了非法的可见内容标记：{marker}")
    for number, marker in _AUDIO_RETENTION_PATTERN.findall(body):
        if marker not in AUDIO_RETENTION_MARKERS:
            warnings.append(f"<Audio {number}> 使用了非法的音频标记：{marker}")

    stamps = [_parse_timestamp(value) for value in _TIMESTAMP_PATTERN.findall(body)]
    if stamps:
        last = max(stamps)
        if last > 0 and not 4.0 <= last <= 15.0 + 0.001:
            warnings.append(f"最后一个切点 {format_timestamp(last)} 落在 H3 建议的单段 4–15 秒之外")
        if duration_seconds and last > float(duration_seconds) + 0.001:
            warnings.append(
                f"时间轴最后切点 {format_timestamp(last)} 超出镜头时长 {float(duration_seconds):g} 秒"
            )

    if len(body) > max_chars:
        warnings.append(f"提示词长度 {len(body)} 超过 H3 上限 {max_chars} 字符")

    words = _count_words(body)
    low, high = word_range_for_duration(duration_seconds)
    if 0 < words < low:
        warnings.append(f"英文正文 {words} 词，低于该时长建议的 {low}–{high} 词区间")

    return _dedupe(warnings)


def validate_h3_base(
    text: str,
    *,
    reference_mode: str = "text_only",
    duration_seconds: float | None = None,
    max_chars: int = H3_MAX_PROMPT_CHARS,
) -> list[str]:
    """校验基础模式提示词的结构与首帧/尾帧对齐句。"""
    warnings: list[str] = []
    body = str(text or "")
    mode = str(reference_mode or "text_only").strip().lower()

    missing = [name for name in BASE_SECTION_ORDER if f"{name}:" not in body]
    if missing:
        warnings.append("缺少 H3 必需段落：" + "、".join(missing))

    positions = [body.find(f"{name}:") for name in BASE_SECTION_ORDER]
    present = [position for position in positions if position >= 0]
    if present != sorted(present):
        warnings.append("H3 段落顺序不符合规范（应为 " + " → ".join(BASE_SECTION_ORDER) + "）")

    if mode in {"first", "key", "first_last", "first_last_key"}:
        if not body.startswith(("For the target video", "How the reference pictures align")):
            warnings.append(f"{mode} 模式缺少官方首帧/首尾帧对齐句")

    if mode == "last":
        if not body.startswith("How the reference pictures align"):
            warnings.append("last 模式缺少官方尾帧对齐句")

    description_body = _section_body(body, "integrated_multimodal_description")
    if "[Shot 1]" not in description_body:
        warnings.append("integrated_multimodal_description 缺少 [Shot 1]")
    if re.search(r"\[Shot 1\]\s*At ", description_body):
        warnings.append("[Shot 1] 不应带时间戳（首个镜头不写 At MM:SS.mmm）")

    d_open, d_close = body.count("<d>"), body.count("</d>")
    if d_open != d_close:
        warnings.append(f"<d> 台词标签未成对闭合（{d_open} 开 / {d_close} 闭）")

    if len(body) > max_chars:
        warnings.append(f"提示词长度 {len(body)} 超过 H3 上限 {max_chars} 字符")

    words = _count_words(body)
    low, high = word_range_for_duration(duration_seconds)
    if 0 < words < low:
        warnings.append(f"英文正文 {words} 词，低于该时长建议的 {low}–{high} 词区间")

    return _dedupe(warnings)


__all__ = [
    "AUDIO_RETENTION_MARKERS",
    "BASE_MODES",
    "BASE_SECTION_ORDER",
    "H3_MAX_PROMPT_CHARS",
    "H3Prose",
    "H3_RECOMMENDED_WORD_RANGE",
    "H3RenderResult",
    "KNOWN_TASK_TYPES",
    "REFERENCE_MODE",
    "REFERENCE_SECTION_ORDER",
    "VISIBLE_RETENTION_MARKERS",
    "build_h3_alignment_instruction",
    "format_seconds",
    "format_timestamp",
    "h3_label_for",
    "render_h3",
    "render_h3_base",
    "render_h3_reference",
    "validate_h3_base",
    "validate_h3_reference",
    "word_range_for_duration",
]
