"""H3 视频提示词 Agent：把分镜 IR 写成 MiniMax H3 官方的英文六段正文。

分工：
- `app/chains/prompts/ir.py` 负责把分镜上下文整理成**与模型无关**的 IR；
- 本 Agent 负责把 IR 写成**符合 H3 官方格式**的英文正文（`H3Prose`）；
- `app/chains/prompts/renderers/h3.py` 负责把正文装配成最终提示词并校验结构。

这样换模型时只需新增「IR → 该模型正文」的 Agent 与渲染器，不必改动分镜链路。

模式差异：
- reference：写六段，`<Subject N>` 定义内容单元，`<Audio N>` 定义音色参考；
- first/last/first_last/text_only：写三段，不使用全参考标签，图片槽位由渲染器补对齐句。
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import PromptTemplate

from app.chains.agents.base import AgentBase
from app.chains.prompts import short_drama_rules as rules
from app.chains.prompts.ir import IRPrompt
from app.chains.prompts.renderers.h3 import H3Prose, word_range_for_duration

_SYSTEM_PROMPT = "\n".join(
    [
        "你是竖屏短剧的分镜视频提示词工程师，负责为 MiniMax H3 视频模型撰写英文提示词正文。",
        "",
        "先判断输入模式，再决定写哪种结构：",
        "- reference：全参考模式，写六段正文；",
        "- first / last / key / first_last / text_only：基础模式，写三段正文。",
        "段落名由系统拼装，你只写各段落的正文，不要输出段落名本身。",
        "",
        "全参考模式（reference）格式纪律：",
        "- 正文一律英文；仅 <d> 内的台词保留原语言；",
        "- subject_definitions：每个内容单元一行，官方写法是 `<Subject N> is ...`；",
        "  由参考图定义的内容单元在行内写来源，如 `in <Picture 1>`；",
        "- 音频参考写成 `<Audio N> is the voice-timbre reference for <Subject N> (S1).`；",
        "  <Audio N> 的编号独立于 <Picture N>，不要混用；",
        "- summary：一段英文，以方括号任务类型前缀开头（如 `[reference generation]`、",
        "  `[reference generation + audio reference]`），只引用已定义的标签；",
        "- retention_analysis：每个 <Subject N> 一行，格式 "
        "`<Subject N> (appears in [Shot 1], [Shot 3]): marker - 说明`；可见内容标记只能用 "
        "fully_preserved / partially_preserved / attribute_transfer / weak_reference；",
        "- retention_analysis 里每个 <Audio N> 一行，格式 `<Audio N>: reference - 说明`；",
        "  音色参考用 reference，不要写 fully_copy；此处不得写 (Sx)；",
        "",
        "基础模式（first/last/key/first_last/text_only）格式纪律：",
        "- 只写 integrated_multimodal_description / overall_soundscape / non_diegetic_music 三段；",
        "- 不要使用 <Subject N>、<Picture N>、<Audio N> 等全参考标签；",
        "- 直接用角色名或稳定的外观描述指代人物；",
        "- 首帧/尾帧对齐句由系统在正文前自动添加，你不要重复写；",
        "",
        "两种模式共用的写作纪律：",
        "- detailed_description / integrated_multimodal_description 先用 1–2 句英文确立风格，",
        "  再写 `[Shot 1]`（首个镜头不带时间戳）；后续镜头写 `[Shot N] At MM:SS.mmm, ...`；",
        "- 运镜写成完整英文自然句：运动类型 + 幅度 + 速度；",
        "- 说话人用稳定的 (S1)/(S2)，台词写成 `<d>[Chinese] …</d>`，逐字保留，不改写、不翻译；",
        "- 旁白写 `says in an off-screen voiceover` 并说明画面人物嘴唇不动；",
        "  画外音写 `says off-screen`；电话声写 `says through a phone speaker`；",
        "- 有 <Audio N> 时，在对应台词前写 `in the voice timbre referenced from <Audio N>`；",
        "- 正文写可见动作、状态变化、空间位置与声音，不写剧情摘要，不写抽象评价词；",
        "- overall_soundscape 只写环境音与物理拟音，不重复台词；",
        "- non_diegetic_music 没有背景音乐就写 N/A；",
        "- 不新增画面内文字、字幕、水印或 UI；对白只放在 <d> 内；",
        "- 不使用 'cinematic' / 'beautiful' / 'high quality' 这类空泛词；",
        "  改用具体的构图、光线、材质、动作与声音细节；",
        "- 正文词数按用户消息里的「正文目标词数」控制；",
        "- 不要输出任何解释、标题或代码块标记。",
        "",
        "短剧写作纪律：",
        rules.summarize_rules(rules.SHORT_DRAMA_SYSTEM_GUIDELINES),
    ]
)

_USER_TEMPLATE = """请为下面这个竖屏短剧镜头撰写 H3 视频提示词正文。

## 基本参数
- 输入模式：{reference_mode}
- 时长：{duration_seconds} 秒
- 画面比例：{aspect_ratio}
- 题材 / 视觉风格：{genre} / {visual_style}
- 正文目标词数：{word_target}

## 参考素材（按上传顺序编号）
{reference_block}

## 图片槽位（首帧/尾帧/关键帧）
{picture_block}

## 内容单元（已分配 H3 标签，参考模式正文必须原样沿用这些标签与编号）
{subject_block}

## 音频参考（音色参考，不是原声复用）
{audio_block}

## 台词
{dialogue_block}

## 镜头信息
{shot_block}

## 短剧写作规则
{rules_block}

## 禁用词
{banned_block}
"""


def _reference_block(ir: IRPrompt) -> str:
    if ir.reference_mode != "reference":
        return "（当前不是 reference 模式，不使用资产参考图标签）"
    if not ir.references:
        return "（本镜头没有可用参考图）"
    lines: list[str] = []
    for index, ref in enumerate(ir.references, start=1):
        lines.append(
            f"{ref.token}（H3 标签 <Picture {index}>）："
            + rules.build_reference_binding_line(ref.token, ref.name, ref.kind)
        )
    return "\n".join(lines)


def _picture_block(ir: IRPrompt) -> str:
    if not ir.pictures:
        return "（当前模式没有首帧/尾帧图片槽位）"
    role_names = {
        "first_frame": "首帧",
        "last_frame": "尾帧",
        "key_frame": "关键帧",
        "composition": "构图锚点",
    }
    return "\n".join(
        f"<{picture.label}> = {role_names.get(picture.role, picture.role)}"
        for picture in ir.pictures
    )


def _subject_block(ir: IRPrompt) -> str:
    lines: list[str] = []
    for subject in ir.subjects:
        speaker = f" speaker={subject.speaker_id}" if subject.speaker_id else ""
        sources = ", ".join(subject.source_tokens) or "-"
        if ir.reference_mode == "reference":
            lines.append(
                f"{subject.label} = {subject.kind}「{subject.name}」sources={sources}{speaker}"
            )
        else:
            lines.append(
                f"{subject.kind}「{subject.name}」description={subject.definition or '-'}{speaker}"
            )
    return "\n".join(lines) or "-"


def _audio_block(ir: IRPrompt) -> str:
    if not ir.audio_references:
        return "（本镜头没有参考音频；不要写 <Audio N>，但台词仍按 <d> 和 (Sx) 写）"
    lines: list[str] = []
    for audio in ir.audio_references:
        lines.append(
            f"<{audio.label}> = 音色参考，speaker={audio.speaker_name} ({audio.speaker_id})"
        )
    return "\n".join(lines)


def _dialogue_block(ir: IRPrompt) -> str:
    lines: list[str] = []
    for shot in ir.shots:
        for line in shot.dialogues:
            emotion = f"（情绪：{line.emotion}）" if line.emotion else ""
            audio = f"，音色参考 {line.audio_label}" if line.audio_label else ""
            mode = str(line.line_mode or "DIALOGUE").upper()
            lines.append(
                f"[Shot {shot.index}] {line.speaker_name} ({line.speaker_id})"
                f"（{mode}{emotion}{audio}）：{line.text}"
            )
    return "\n".join(lines) or "（本镜头没有台词）"


def _shot_block(ir: IRPrompt) -> str:
    blocks: list[str] = []
    for shot in ir.shots:
        blocks.append(
            "\n".join(
                [
                    f"[Shot {shot.index}] start={shot.start_seconds:g}s",
                    f"shot_size={shot.shot_size or '-'} angle={shot.camera_angle or '-'} "
                    f"movement={shot.camera_movement or '-'}",
                    f"location={shot.location or '-'}",
                    f"visual={shot.visual or '-'}",
                    "action_beats=" + (" / ".join(shot.action_beats) or "-"),
                    f"atmosphere={shot.atmosphere or '-'}",
                    f"composition_anchor={shot.composition_anchor or '-'}",
                    f"screen_direction={shot.screen_direction or '-'}",
                    f"continuity={shot.continuity or '-'}",
                ]
            )
        )
    return "\n\n".join(blocks) or "-"


def _rules_block(ir: IRPrompt) -> str:
    del ir
    return "\n".join(
        [
            "【竖屏构图】",
            rules.summarize_rules(rules.VERTICAL_FRAME_RULES),
            "【情绪写行为】",
            rules.summarize_rules(rules.EMOTION_AS_BEHAVIOR_RULES),
            "【短剧节奏】",
            rules.summarize_rules(rules.PACING_RULES),
            "【负面约束写法】",
            rules.summarize_rules(rules.NEGATIVE_PROMPT_DISCIPLINE),
        ]
    )


def build_h3_agent_variables(ir: IRPrompt) -> dict[str, str]:
    """把 IR 整理成 Agent 提示词变量（纯函数）。"""
    low, high = word_range_for_duration(ir.duration_seconds)
    return {
        "reference_mode": ir.reference_mode,
        "duration_seconds": f"{ir.duration_seconds:g}",
        "aspect_ratio": ir.aspect_ratio or "9:16",
        "genre": ir.genre or "-",
        "visual_style": ir.visual_style or "-",
        "word_target": f"{low}–{high}",
        "reference_block": _reference_block(ir),
        "picture_block": _picture_block(ir),
        "subject_block": _subject_block(ir),
        "audio_block": _audio_block(ir),
        "dialogue_block": _dialogue_block(ir),
        "shot_block": _shot_block(ir),
        "rules_block": _rules_block(ir),
        "banned_block": "、".join(rules.BANNED_ABSTRACT_WORDS) or "-",
    }


class H3VideoPromptAgent(AgentBase[H3Prose]):

    """把分镜 IR 写成 H3 官方英文正文。"""

    # 注册表键：发布后的模板提示词覆盖代码默认（见 prompt_registry.py）
    agent_key = 'h3_video'

    @property
    def output_model(self) -> type[H3Prose]:
        return H3Prose

    def _default_system_prompt(self) -> str:
        return _SYSTEM_PROMPT

    @property
    def prompt_template(self) -> PromptTemplate:
        return PromptTemplate.from_template(_USER_TEMPLATE)

    def render_from_ir(self, ir: IRPrompt) -> str:
        """按 IR 渲染完整提示词（便于预览与排障）。"""
        return self.render_prompt(**build_h3_agent_variables(ir))


async def generate_h3_prose(
    llm: BaseChatModel,
    ir: IRPrompt,
) -> tuple[H3Prose | None, list[str]]:
    """调用 LLM 生成 H3 正文；失败时返回 (None, 警告)，由渲染器回落到结构骨架。"""
    agent = H3VideoPromptAgent(llm)
    try:
        prose = await agent.aextract(**build_h3_agent_variables(ir))
    except Exception as exc:  # noqa: BLE001 - 任何失败都应降级为骨架，不阻断生成链路
        return None, [f"H3 英文正文生成失败，已回落到结构骨架：{exc}"]
    if not isinstance(prose, H3Prose):
        return None, ["H3 英文正文为空，已回落到结构骨架"]
    main_body = (
        prose.detailed_description
        if ir.reference_mode == "reference"
        else prose.integrated_multimodal_description
    )
    if not str(main_body or "").strip():
        return None, ["H3 英文正文为空，已回落到结构骨架"]
    return prose, []


__all__ = [
    "H3VideoPromptAgent",
    "build_h3_agent_variables",
    "generate_h3_prose",
]
