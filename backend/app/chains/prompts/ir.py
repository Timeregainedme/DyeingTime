"""提示词中间表示（IR）。

设计目标：把「写什么」与「写给哪个模型」解耦。

- 构建端（`build_video_prompt_ir`）只负责把业务数据（`ShotVideoPromptPackRead`、
  台词行、项目风格、参考素材）整理成结构化文档，不含任何模型特有格式；
- 渲染端（`app.chains.prompts.renderers`）负责把同一份 IR 输出为目标模型所需格式。

这样新增或更换图片/视频模型时，只需要新增一个 renderer，上游构建逻辑保持不变。

术语对齐 H3 官方规范：`references` 对应参考素材（内部统一用 `图N` 有序 token），
`subjects` 对应 `<Subject N>` 定义的内容单元，`audio_references` 对应 `<Audio N>` 音色参考，
`pictures` 对应首帧/尾帧/关键帧槽位，`shots` 对应 `[Shot N]` 段落。
"""

from __future__ import annotations

from typing import Any, Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field

from app.chains.prompts import short_drama_rules as rules
from app.schemas.studio.shots import ShotVideoPromptPackRead

IRReferenceKind = Literal["character", "scene", "prop", "costume", "frame"]
IRReferenceMode = Literal[
    "reference",
    "first",
    "last",
    "key",
    "first_last",
    "first_last_key",
    "text_only",
]
IRPictureRole = Literal["first_frame", "last_frame", "key_frame", "composition"]

# H3 参考素材上限（图片 ≤9）。其它模型可在 renderer 里再收紧。
MAX_REFERENCE_IMAGES = rules.MAX_REFERENCE_IMAGES

DEFAULT_VIDEO_DURATION_SECONDS = 5.0

# 默认单镜头连续生成约束。场景已知时带上场景名，避免模型把背景理解成抽象“某个地方”；
# 场景未知时不虚构地点，只要求同一连续空间与一致背景。
DEFAULT_CONTINUITY_WITH_SCENE = (
    "Keep the entire video in one continuous scene at {scene}; "
    "keep the background layout, lighting direction and character positions consistent; "
    "use continuous camera movement and do not cut to another location."
)
DEFAULT_CONTINUITY_WITHOUT_SCENE = (
    "Keep one continuous scene and consistent background; do not cut to another location."
)

_REFERENCE_MODES = {"reference", "first", "last", "key", "first_last", "first_last_key", "text_only"}


class IRReference(BaseModel):
    """一条有序参考素材。`token` 是内部统一 token（`图1`），渲染器再映射为目标模型语法。"""

    model_config = ConfigDict(extra="forbid")

    token: str = Field(..., description="内部统一 token，如 图1")
    kind: IRReferenceKind = Field(..., description="参考素材类型")
    name: str = Field(..., description="资产名称")
    ref_id: str = Field("", description="实体 ID（无实体时为空）")
    file_id: str | None = Field(None, description="提交给模型的文件 ID")
    binding: str = Field("", description="一行绑定说明（token 的实际用途）")


class IRDialogueInput(BaseModel):
    """构建 IR 时的台词输入（来自 shot_dialog_lines）。"""

    model_config = ConfigDict(extra="forbid")

    speaker_character_id: str = Field("", description="结构化说话角色 ID")
    speaker_name: str = Field("", description="说话人名称")
    text: str = Field("", description="台词文本")
    voice_description: str = Field("", description="用户配置的角色声音描述")
    emotion: str | None = Field(None, description="情绪/语气")
    line_mode: str = Field("DIALOGUE", description="对白模式：DIALOGUE/VOICE_OVER/OFF_SCREEN/PHONE")
    audio_file_id: str | None = Field(None, description="该台词已生成配音的文件 ID（用作音色参考）")


class IRAudioReference(BaseModel):
    """一条音频参考（当前只用于音色参考，不复用原声）。"""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(..., description="H3 音频标签，如 Audio 1")
    file_id: str = Field(..., description="音频文件 ID")
    speaker_name: str = Field("", description="对应说话人名称")
    speaker_id: str = Field("", description="稳定说话人编号，如 S1")
    role: Literal["timbre"] = Field("timbre", description="参考用途：音色参考")
    source_line_index: int | None = Field(None, description="来源台词行号，便于诊断")


class IRPicture(BaseModel):
    """首帧/尾帧/关键帧槽位；用于 I2VA/FL2VA/L2VA 的对齐句。"""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(..., description="H3 图片标签，如 Picture 1")
    role: IRPictureRole = Field(..., description="图片在视频中的角色")
    source_token: str = Field("", description="内部 token（如 图1），无则为空")


class IRDialogueLine(BaseModel):
    """IR 中的一条台词，带稳定说话人编号。"""

    model_config = ConfigDict(extra="forbid")

    speaker_name: str = Field(..., description="说话人名称")
    speaker_id: str = Field(..., description="稳定说话人编号，如 S1")
    speaker_character_id: str = Field("", description="结构化说话角色 ID")
    voice_description: str = Field("", description="用户配置的角色声音描述")
    text: str = Field(..., description="台词文本")
    language: str = Field("Chinese", description="台词语言（H3 需要显式语言标签）")
    emotion: str | None = Field(None, description="情绪/语气")
    start_seconds: float | None = Field(None, description="该台词在镜头内的起始秒数")
    line_mode: str = Field("DIALOGUE", description="对白模式：DIALOGUE/VOICE_OVER/OFF_SCREEN/PHONE")
    audio_file_id: str | None = Field(None, description="该台词已生成配音的文件 ID（内部映射用）")
    audio_label: str | None = Field(None, description="该说话人对应的音频标签，如 Audio 1")


class IRSubjectDefinition(BaseModel):
    """一个可复用的内容单元（角色/场景/道具/服装），对应 H3 的 `<Subject N>`。"""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(..., description="内容单元标签，如 Subject 1")
    name: str = Field(..., description="资产名称")
    kind: IRReferenceKind = Field(..., description="内容单元类型")
    definition: str = Field("", description="定义（外观/空间/结构/形制）")
    source_tokens: list[str] = Field(default_factory=list, description="定义该内容单元的参考 token 列表")
    retention: str = Field("fully_preserved", description="保留程度标记")
    appears_in: list[int] = Field(default_factory=list, description="出现的镜头序号（1 基）")
    speaker_id: str | None = Field(None, description="角色作为说话人时的稳定编号，如 S1")


class IRShot(BaseModel):
    """IR 中的一个镜头段落。单次视频生成任务通常只有一个镜头。"""

    model_config = ConfigDict(extra="forbid")

    index: int = Field(..., description="镜头序号（1 基）")
    start_seconds: float = Field(0.0, description="该镜头起始秒数")
    shot_size: str = Field("", description="景别")
    camera_angle: str = Field("", description="机位角度")
    camera_movement: str = Field("", description="运镜方式")
    location: str = Field("", description="场景名称")
    subjects: list[str] = Field(default_factory=list, description="本镜头出现的内容单元标签")
    visual: str = Field("", description="画面描述（本镜头发生了什么）")
    action_beats: list[str] = Field(default_factory=list, description="动作节拍")
    atmosphere: str = Field("", description="氛围")
    composition_anchor: str = Field("", description="构图锚点")
    screen_direction: str = Field("", description="朝向与视线")
    continuity: str = Field("", description="与相邻镜头的连续性要求")
    dialogues: list[IRDialogueLine] = Field(default_factory=list, description="本镜头台词")
    sound: str = Field("", description="本镜头同期声/拟音")


class IRPrompt(BaseModel):
    """一条目标模型无关的提示词 IR。"""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["video", "image"] = Field("video", description="提示词类别")
    reference_mode: IRReferenceMode = Field("reference", description="输入模式，决定 H3 走参考六段还是基础三段")
    task_types: list[str] = Field(default_factory=lambda: ["reference generation"], description="任务类型前缀")
    duration_seconds: float = Field(DEFAULT_VIDEO_DURATION_SECONDS, description="目标时长（秒）")
    aspect_ratio: str | None = Field(None, description="画面比例")
    style_anchor: str = Field("", description="视觉风格锚点")
    genre: str = Field("", description="题材风格（如 真人都市）")
    visual_style: str = Field("", description="视觉风格（现实/动漫）")
    references: list[IRReference] = Field(default_factory=list, description="有序参考素材")
    audio_references: list[IRAudioReference] = Field(default_factory=list, description="音频参考（音色参考）")
    pictures: list[IRPicture] = Field(default_factory=list, description="首帧/尾帧/关键帧槽位")
    subjects: list[IRSubjectDefinition] = Field(default_factory=list, description="内容单元定义")
    shots: list[IRShot] = Field(default_factory=list, description="镜头段落")
    soundscape: str = Field("", description="全片环境音与物理音")
    non_diegetic_music: str = Field("", description="仅观众可听的背景音乐；无则 N/A")
    preserve: list[str] = Field(default_factory=list, description="不可漂移项")
    avoid: list[str] = Field(default_factory=list, description="本镜头定向规避项")
    negative_prompt: str = Field("", description="上游提供的负面提示词原文")
    warnings: list[str] = Field(default_factory=list, description="构建期发现的非阻塞提示")
    source: dict[str, Any] = Field(default_factory=dict, description="诊断用来源信息")

    def reference_tokens(self) -> list[str]:
        return [item.token for item in self.references]

    def subject_for_name(self, name: str) -> IRSubjectDefinition | None:
        for item in self.subjects:
            if item.name == name:
                return item
        return None


def _shot_script_corpus(pack: ShotVideoPromptPackRead) -> str:
    """本镜头自身的剧本语料，用于判断某个角色是否真的在本镜头出场。

    只取本镜头的标题、剧本摘录、镜头描述、动作拍点与对白摘要；
    刻意不含前后镜头摘要——相邻镜头出现的角色不代表本镜头出场。
    """
    parts = [
        pack.title,
        pack.script_excerpt,
        pack.shot_description,
        *pack.action_beats,
        pack.dialogue_summary,
    ]
    return "\n".join(str(part or "") for part in parts)


def _character_appears_in_shot(*, name: str, corpus: str) -> bool:
    """剧本命中判定：本镜头文本里出现该角色名（角色有台词时同样命中）。"""
    target = str(name or "").strip()
    if not target:
        return False
    return target in corpus


def _collect_asset_references(
    pack: ShotVideoPromptPackRead,
    *,
    max_references: int,
) -> tuple[list[IRReference], list[str]]:
    """按「角色 → 场景 → 道具 → 服装」顺序收集带图资产，并分配 `图N` token。

    角色卡需要「关联 + 剧本命中」双重判定：既要在镜头里关联了这个角色，
    还要本镜头剧本内容（标题/摘录/描述/动作拍点/对白）里真的出现该角色名，
    避免纯空镜或只有环境描述的镜头被迫带上无关人物卡。
    """
    warnings: list[str] = []
    ordered: list[tuple[str, str, str, str | None, str]] = []

    corpus = _shot_script_corpus(pack)
    for item in pack.characters:
        if not _character_appears_in_shot(name=item.name, corpus=corpus):
            warnings.append(
                f"角色「{item.name}」已关联该镜头，但本镜头剧本内容里没有出现，本次未插入该角色卡"
            )
            continue
        ordered.append(("character", item.name, "", item.file_id, item.description))
    if pack.scene is not None:
        ordered.append(("scene", pack.scene.name, "", pack.scene.file_id, pack.scene.description))
    for item in pack.props:
        ordered.append(("prop", item.name, "", item.file_id, item.description))
    for item in pack.costumes:
        ordered.append(("costume", item.name, "", item.file_id, item.description))

    with_files = [row for row in ordered if row[3]]
    skipped = len(ordered) - len(with_files)
    if skipped > 0:
        warnings.append(f"{skipped} 项已关联资产还没有可用参考图，本次未纳入参考绑定")

    if len(with_files) > max_references:
        warnings.append(
            f"参考素材超过目标模型上限（{len(with_files)} > {max_references}），已按顺序截断"
        )
        with_files = with_files[:max_references]

    references: list[IRReference] = []
    for index, (kind, name, ref_id, file_id, _description) in enumerate(with_files, start=1):
        token = f"{rules.REFERENCE_TOKEN_PREFIX}{index}"
        references.append(
            IRReference(
                token=token,
                kind=kind,  # type: ignore[arg-type]
                name=name,
                ref_id=ref_id,
                file_id=file_id,
                binding=rules.build_reference_binding_line(token, name, kind),
            )
        )
    return references, warnings


def _definition_rows(pack: ShotVideoPromptPackRead) -> list[tuple[str, str, str]]:
    """列出上下文包里所有可用于内容单元定义的资产（不要求有参考图）。"""
    rows: list[tuple[str, str, str]] = []
    for item in pack.characters:
        rows.append(("character", item.name, item.description or ""))
    if pack.scene is not None:
        rows.append(("scene", pack.scene.name, pack.scene.description or ""))
    for item in pack.props:
        rows.append(("prop", item.name, item.description or ""))
    for item in pack.costumes:
        rows.append(("costume", item.name, item.description or ""))
    return rows


def _appears_in(name: str, shots: list[IRShot]) -> list[int]:
    """判断内容单元出现在哪些镜头；找不到时默认全镜头。"""
    appears = [shot.index for shot in shots if name and name in shot.visual]
    return appears or [shot.index for shot in shots]


def _build_subjects(
    pack: ShotVideoPromptPackRead,
    *,
    references: list[IRReference],
    shots: list[IRShot],
    include_without_reference: bool = False,
) -> list[IRSubjectDefinition]:
    """把参考素材（以及非参考模式下的资产描述）提升为内容单元定义。

    参考模式只定义真正有参考图的单元；首尾帧/纯文本模式没有参考图编号，
    但仍需要角色/场景描述供正文写作，因此按 `include_without_reference` 补齐。
    """
    descriptions = {(kind, name): description for kind, name, description in _definition_rows(pack)}
    subjects: list[IRSubjectDefinition] = []
    referenced_names: set[str] = set()

    for ref in references:
        referenced_names.add(ref.name)
        subjects.append(
            IRSubjectDefinition(
                label=f"Subject {len(subjects) + 1}",
                name=ref.name,
                kind=ref.kind,
                definition=descriptions.get((ref.kind, ref.name), ""),
                source_tokens=[ref.token],
                retention="fully_preserved",
                appears_in=_appears_in(ref.name, shots),
            )
        )

    if include_without_reference:
        for kind, name, description in _definition_rows(pack):
            if not name or name in referenced_names:
                continue
            subjects.append(
                IRSubjectDefinition(
                    label=f"Subject {len(subjects) + 1}",
                    name=name,
                    kind=kind,  # type: ignore[arg-type]
                    definition=description,
                    source_tokens=[],
                    retention="fully_preserved",
                    appears_in=_appears_in(name, shots),
                )
            )
    return subjects


def _build_dialogues(
    dialogues: Sequence[IRDialogueInput],
    *,
    subjects: list[IRSubjectDefinition],
) -> tuple[list[IRDialogueLine], list[str]]:
    """按首次出现顺序分配稳定说话人编号，并把编号回填到角色内容单元。"""
    warnings: list[str] = []
    speaker_ids: dict[str, str] = {}
    lines: list[IRDialogueLine] = []

    for item in dialogues:
        text = str(item.text or "").strip()
        if not text:
            continue
        name = str(item.speaker_name or "").strip() or "角色"
        if name not in speaker_ids:
            speaker_ids[name] = f"S{len(speaker_ids) + 1}"
        lines.append(
            IRDialogueLine(
                speaker_name=name,
                speaker_id=speaker_ids[name],
                speaker_character_id=str(item.speaker_character_id or "").strip(),
                voice_description=str(item.voice_description or "").strip(),
                text=text,
                emotion=item.emotion,
                line_mode=str(item.line_mode or "DIALOGUE").strip().upper() or "DIALOGUE",
                audio_file_id=str(item.audio_file_id or "").strip() or None,
                audio_label=None,
            )
        )

    for subject in subjects:
        if subject.kind == "character" and subject.name in speaker_ids:
            subject.speaker_id = speaker_ids[subject.name]

    unbound = [name for name in speaker_ids if not any(s.name == name for s in subjects)]
    if unbound:
        warnings.append(f"说话人 {'、'.join(unbound)} 没有对应的角色参考资产，参考模式下无法绑定音色/外观")
    return lines, warnings


def _build_pictures(reference_mode: str) -> list[IRPicture]:
    """按输入模式生成 H3 图片槽位；参考模式不使用独立 Picture 定义。"""
    mode = str(reference_mode or "").strip().lower()
    if mode in {"first", "key"}:
        return [IRPicture(label="Picture 1", role="first_frame")]
    if mode == "last":
        return [IRPicture(label="Picture 1", role="last_frame")]
    if mode == "first_last":
        return [
            IRPicture(label="Picture 1", role="first_frame"),
            IRPicture(label="Picture 2", role="last_frame"),
        ]
    if mode == "first_last_key":
        return [
            IRPicture(label="Picture 1", role="first_frame"),
            IRPicture(label="Picture 2", role="last_frame"),
            IRPicture(label="Picture 3", role="key_frame"),
        ]
    return []


def _build_audio_references(
    dialogues: Sequence[IRDialogueLine],
    *,
    audio_file_ids: Sequence[str],
) -> tuple[list[IRAudioReference], list[str]]:
    """把实际提交的参考音频绑定到说话人。

    规则：按台词顺序扫描，同一说话人只取第一条有配音的台词；最多 3 条。
    这样 `<Audio N>` 与 `(Sx)` 才能稳定对应，不会让同一个角色占多个音频位。
    """
    wanted = [str(item).strip() for item in audio_file_ids if str(item).strip()]
    if not wanted:
        return [], []

    warnings: list[str] = []
    wanted_set = set(wanted)
    seen_speakers: set[str] = set()
    audio_refs: list[IRAudioReference] = []
    matched_file_ids: set[str] = set()

    for line in dialogues:
        file_id = str(line.audio_file_id or "").strip()
        if not file_id or file_id not in wanted_set:
            continue
        if line.speaker_id in seen_speakers:
            continue
        seen_speakers.add(line.speaker_id)
        matched_file_ids.add(file_id)
        label = f"Audio {len(audio_refs) + 1}"
        line.audio_label = label
        audio_refs.append(
            IRAudioReference(
                label=label,
                file_id=file_id,
                speaker_name=line.speaker_name,
                speaker_id=line.speaker_id,
                source_line_index=None,
            )
        )
        if len(audio_refs) >= 3:
            break

    # 显式传入的音频可能没有回填到台词行（历史数据/手工选择）：
    # 此时按台词顺序绑定到尚未占用的说话人，避免音频提交了却不在提示词里引用。
    if not matched_file_ids and dialogues:
        assigned_speakers: set[str] = set()
        for file_id in wanted:
            line = next(
                (
                    item
                    for item in dialogues
                    if item.speaker_id and item.speaker_id not in assigned_speakers
                ),
                None,
            )
            if line is None:
                break
            assigned_speakers.add(line.speaker_id)
            matched_file_ids.add(file_id)
            label = f"Audio {len(audio_refs) + 1}"
            line.audio_label = label
            audio_refs.append(
                IRAudioReference(
                    label=label,
                    file_id=file_id,
                    speaker_name=line.speaker_name,
                    speaker_id=line.speaker_id,
                    source_line_index=None,
                )
            )
            if len(audio_refs) >= 3:
                break
        if audio_refs:
            warnings.append("参考音频未回填到台词行，已按台词顺序绑定到说话人")

    # 同一说话人的后续台词沿用同一个 <Audio N>，保证口型/音色引用稳定。
    label_by_speaker = {item.speaker_id: item.label for item in audio_refs if item.speaker_id}
    for line in dialogues:
        if line.speaker_id in label_by_speaker:
            line.audio_label = label_by_speaker[line.speaker_id]

    missing = [file_id for file_id in wanted if file_id not in matched_file_ids]
    if missing:
        warnings.append(
            f"{len(missing)} 条参考音频没有匹配到台词说话人，本次未写入 <Audio N>："
            + "、".join(missing)
        )
    return audio_refs, warnings


def build_video_prompt_ir(
    pack: ShotVideoPromptPackRead,
    *,
    dialogues: Sequence[IRDialogueInput] = (),
    reference_mode: str = "reference",
    audio_file_ids: Sequence[str] = (),
    duration_seconds: float | None = None,
    aspect_ratio: str | None = None,
    max_references: int = MAX_REFERENCE_IMAGES,
    references_override: Sequence[IRReference] | None = None,
    natural_prompt: str | None = None,
    audio_references_override: Sequence[IRAudioReference] | None = None,
) -> IRPrompt:
    """把视频提示词上下文包整理成 IR。

    本函数是纯函数：不访问数据库、不发起网络请求。
    参考模式把资产图转成 `<Subject N>` / `<Picture N>`；首尾帧与纯文本模式只保留
    帧槽位和文字描述，避免把分镜帧误标成参考资产。
    """
    warnings: list[str] = []

    mode = str(reference_mode or "reference").strip().lower()
    if mode not in _REFERENCE_MODES:
        warnings.append(f"未知 reference_mode={reference_mode!r}，已按 reference 处理")
        mode = "reference"

    duration = float(duration_seconds or pack.camera.duration or DEFAULT_VIDEO_DURATION_SECONDS)
    if duration <= 0:
        duration = DEFAULT_VIDEO_DURATION_SECONDS
        warnings.append("镜头时长缺失或非法，已按默认 5 秒构建 IR")

    if mode == "reference":
        if references_override is not None:
            references = list(references_override)
            if len(references) > max_references:
                warnings.append(
                    f"参考素材超过目标模型上限（{len(references)} > {max_references}），已按顺序截断"
                )
                references = references[:max_references]
        else:
            references, ref_warnings = _collect_asset_references(pack, max_references=max_references)
            warnings.extend(ref_warnings)
    else:
        references = []

    shot_description = str(getattr(pack, "shot_description", "") or "").strip()
    visual = str(natural_prompt or "").strip() or shot_description or str(pack.script_excerpt or "").strip()

    shot = IRShot(
        index=1,
        start_seconds=0.0,
        shot_size=pack.camera.camera_shot,
        camera_angle=pack.camera.angle,
        camera_movement=pack.camera.movement,
        location=pack.scene.name if pack.scene else "",
        subjects=[ref.name for ref in references if ref.name],
        visual=visual,
        action_beats=list(pack.action_beats),
        atmosphere=pack.atmosphere,
        composition_anchor=pack.composition_anchor,
        screen_direction=pack.screen_direction_guidance,
        continuity=pack.continuity_guidance,
    )
    # 默认单镜头连续生成：不主动要求 H3 在同一条短视频内切换机位/场景；
    # 高级多机位需求仍可通过自然提示词/高级提示词显式表达。
    shot.continuity = " ".join(
        part for part in [
            str(shot.continuity or "").strip(),
            (
                DEFAULT_CONTINUITY_WITH_SCENE.format(scene=pack.scene.name)
                if pack.scene is not None
                else DEFAULT_CONTINUITY_WITHOUT_SCENE
            ),
        ] if part
    )

    subjects = _build_subjects(
        pack,
        references=references,
        shots=[shot],
        include_without_reference=(mode != "reference"),
    )
    dialogue_lines, dialogue_warnings = _build_dialogues(dialogues, subjects=subjects)
    warnings.extend(dialogue_warnings)
    shot.dialogues = dialogue_lines
    if not dialogue_lines and not str(shot.sound or "").strip():
        shot.sound = "No spoken dialogue is requested; characters do not speak. Use only ambient room tone and natural physical sounds."

    # 首尾帧/纯文本模式不使用全参考标签，参考音频也就没有合法的 <Audio N> 位置。
    audio_refs: list[IRAudioReference] = []
    if mode == "reference":
        audio_refs, audio_warnings = _build_audio_references(
            dialogue_lines,
            audio_file_ids=audio_file_ids,
        )
        warnings.extend(audio_warnings)
    elif audio_file_ids:
        warnings.append("当前输入模式不是 reference，参考音频不会写入提示词")

    task_types: list[str] = []
    if mode == "reference" and references:
        task_types.append("reference generation")
    if audio_refs:
        task_types.append("audio reference")
    if not task_types and mode != "text_only":
        task_types.append("keyframe completion")

    return IRPrompt(
        kind="video",
        reference_mode=mode,  # type: ignore[arg-type]
        task_types=task_types,
        duration_seconds=duration,
        aspect_ratio=aspect_ratio,
        style_anchor=" ".join(part for part in [pack.visual_style, pack.style] if part).strip(),
        genre=pack.style,
        visual_style=pack.visual_style,
        references=references,
        audio_references=audio_refs,
        pictures=_build_pictures(mode),
        subjects=subjects,
        shots=[shot],
        soundscape=shot.sound,
        non_diegetic_music="N/A",
        preserve=list(rules.DEFAULT_PRESERVE_ITEMS),
        avoid=list(rules.DEFAULT_AVOID_ITEMS),
        negative_prompt=pack.negative_prompt,
        warnings=warnings,
        source={
            "shot_id": pack.shot_id,
            "title": pack.title,
            "reference_mode": mode,
            "duration_seconds": duration,
            "natural_prompt": str(natural_prompt or "").strip(),
        },
    )


def dialogues_from_summary(summary: str) -> list[IRDialogueInput]:
    """把上下文案里的 `角色：台词` 摘要还原成结构化对白输入。

    `ShotVideoPromptPackRead.dialogue_summary` 是提示词上下文包里唯一携带对白的字段
    （格式由 `shot_video_prompt_pack.build_shot_video_prompt_pack` 生成）。IR 需要结构化的
    说话人与文本才能分配稳定的 `(Sx)`，因此在这里做一次显式还原。
    """
    items: list[IRDialogueInput] = []
    for raw in str(summary or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        separator = "：" if "：" in line else (":" if ":" in line else "")
        if separator:
            speaker, _, text = line.partition(separator)
        else:
            speaker, text = "", line
        text = text.strip()
        if not text:
            continue
        items.append(IRDialogueInput(speaker_name=speaker.strip() or "角色", text=text))
    return items


__all__ = [
    "DEFAULT_VIDEO_DURATION_SECONDS",
    "IRAudioReference",
    "IRDialogueInput",
    "IRDialogueLine",
    "IRPicture",
    "IRPictureRole",
    "IRPrompt",
    "IRReference",
    "IRReferenceKind",
    "IRReferenceMode",
    "IRShot",
    "IRSubjectDefinition",
    "MAX_REFERENCE_IMAGES",
    "build_video_prompt_ir",
    "dialogues_from_summary",
]
