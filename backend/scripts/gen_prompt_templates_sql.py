"""生成图片提示词模板迁移 SQL。

为什么用生成器而不是手写：
- 帧提示词模板（B1）的权威文本在 `app/chains/agents/shot_frame_prompt_agents.py` 里，
  手抄一份进 SQL 必然漂移；这里直接 import 常量，保证 SQL 与代码逐字一致。
- 资产模板（C1）以「交付物 → 参考图角色 → 主体与细节 → 统一约束」结构版本化，
  便于回溯与批量更新。
- 视频提示词（video_prompt）**故意不播种**：视频提示词由 IR → H3 渲染器生成，
  一旦数据库存在 video_prompt 模板就会走模板分支把 IR 链路绕过去。

迁移约定：`012` 是已应用的种子文件，不再修改；新模板变更写入新的迁移文件。
默认输出 `028-rewrite-image-prompt-templates.sql`。

用法：
    cd backend
    .venv/bin/python scripts/gen_prompt_templates_sql.py
    .venv/bin/python scripts/gen_prompt_templates_sql.py \
        --output 030-next-image-prompt-change.sql \
        --title "030-next-image-prompt-change.sql"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.chains.agents.shot_frame_prompt_agents import (  # noqa: E402
    _KEY_FRAME_TEMPLATE,
    _LAST_FRAME_TEMPLATE,
    _FIRST_FRAME_TEMPLATE,
    _SHOT_FRAME_INPUT_VARS,
)

# 资产模板通用变量（与 build_prompt_with_template 传入的 variables 对齐）
ASSET_VARS = [
    "name",
    "description",
    "tags",
    "visual_style",
    "style",
    "view_angle",
    "quality_level",
    "format",
    "style_pack",
    "reference_block",
    "negative_prompt",
]

# 所有图片模板共用的画面文字约束：不生成文字，也不改写参考资产里已有的文字。
NO_TEXT_CONSTRAINTS = """- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘"""

ASSET_TEMPLATES: dict[str, tuple[str, str, list[str], str]] = {
    "actor_image_front": (
        "演员正面图片提示词",
        "演员正面定妆照",
        ASSET_VARS,
        """{{ style_pack }}

[交付物]
演员正面定妆照：正面平视半身，纯色中性背景，脚下有自然接触阴影。

[参考图角色]
{{ reference_block }}

[主体与细节]
{{ description }}
- 正面平视机位，双眼直视镜头，肩线水平，构图居中偏上
- 面部细节清晰可辨：眼型、眉形、鼻梁、唇形、下颌线与发际线
- 柔和均匀的主光加一侧补光，面部无硬阴影、无油光、无过曝
- 服装平整，发型完整，不出现手持道具
- 写实皮肤质感，保留真实毛孔与细纹，不做磨皮

[Constraints]
- 保持面部五官、发型发色、肤色与年龄感不变
""" + NO_TEXT_CONSTRAINTS + """
- 避免出现：{{ negative_prompt }}""",
    ),
    "actor_image_other": (
        "演员侧面/后面图片提示词",
        "演员非正面视角",
        ASSET_VARS,
        """{{ style_pack }}

[交付物]
同一演员的{{ view_angle }}定妆照：画面只呈现该视角应有的信息。

[参考图角色]
{{ reference_block }}

[主体与细节]
仅修改：视角为{{ view_angle }}；头部、颈部与肩部朝向符合该视角，透视与轮廓正确，无面部扭曲。
保留：脸型、五官比例、发型发色、肤色、年龄感、服装、背景、光照方向、人物比例。
{{ description }}
- 不得残留正面元素，不出现正脸、不出现双眼直视镜头
- 不出现手持道具

[Constraints]
- 保持与正面图完全同一个人，身份严格一致
""" + NO_TEXT_CONSTRAINTS + """
- 避免出现：{{ negative_prompt }}""",
    ),
    "character_image_front": (
        "角色正面图片提示词",
        "角色正面定妆照（身份锁定）",
        ASSET_VARS,
        """{{ style_pack }}

[交付物]
角色定妆照：正面平视半身，纯色中性背景，脚下有自然接触阴影。

[参考图角色]
{{ reference_block }}

[主体与细节]
{{ description }}
- 正面平视机位，双眼直视镜头，肩线水平，构图居中偏上
- 面部细节清晰可辨：眼型、眉形、鼻梁、唇形、下颌线与发际线
- 柔和均匀的主光加一侧补光，面部无硬阴影、无油光、无过曝
- 服装平整，发型完整，不出现手持道具
- 写实皮肤质感，保留真实毛孔与细纹，不做磨皮

[Constraints]
- 参考图中的人物即为本角色「{{ name }}」的身份基准；只约束长相、发型、发色、肤色、体型与年龄
- 不得换脸、不得改变发型发色与年龄感；参考图包含服装时沿用该服装
""" + NO_TEXT_CONSTRAINTS + """
- 避免出现：{{ negative_prompt }}""",
    ),
    "character_image_other": (
        "角色侧面/后面图片提示词",
        "角色非正面视角（身份锁定）",
        ASSET_VARS,
        """{{ style_pack }}

[交付物]
同一角色的{{ view_angle }}定妆照：画面只呈现该视角应有的信息。

[参考图角色]
{{ reference_block }}

[主体与细节]
仅修改：视角为{{ view_angle }}；头部、颈部与肩部朝向符合该视角，透视与轮廓正确，无面部扭曲。
保留：脸型、五官比例、发型发色、肤色、年龄感、服装形制与颜色、背景、光照方向、人物比例。
{{ description }}
- 不得残留正面元素，不出现正脸、不出现双眼直视镜头
- 不出现手持道具

[Constraints]
- 与角色正面定妆照完全同一个人，身份、服装与比例严格一致
""" + NO_TEXT_CONSTRAINTS + """
- 避免出现：{{ negative_prompt }}""",
    ),
    "prop_image_front": (
        "道具图片提示词",
        "高质量道具特写",
        ASSET_VARS,
        """{{ style_pack }}

[交付物]
道具独立静物图：主体居中，简洁环境背景，完整入画不被裁切。

[参考图角色]
{{ reference_block }}

[主体与细节]
{{ description }}
- 镜头方向：正面；结构、比例与关键细节清楚
- 材质交代明确：金属反光、皮革纹理、玻璃折射、布料纤维与磨损细节可见
- 柔和的侧上方主光，轮廓光勾边，主体与背景分离清楚
- 除道具本身外不加多余元素，不出现手持痕迹

[Constraints]
- 保持道具的形制、颜色、材质与磨损状态不变
""" + NO_TEXT_CONSTRAINTS + """
- 避免出现：{{ negative_prompt }}""",
    ),
    "prop_image_other": (
        "道具侧面/后面图片提示词",
        "道具非正面视角",
        ASSET_VARS,
        """{{ style_pack }}

[交付物]
同一道具的{{ view_angle }}静物图：完整入画，结构对应。

[参考图角色]
{{ reference_block }}

[主体与细节]
仅修改：视角为{{ view_angle }}；只呈现该视角应有的信息，不残留正面特征。
保留：形制、颜色、材质、磨损状态、比例与关键纹样。
{{ description }}
- 透视正确，结构关系合理
- 不出现手持痕迹

[Constraints]
- 与正面图完全同一个道具，形制、颜色、材质与磨损状态严格一致
""" + NO_TEXT_CONSTRAINTS + """
- 避免出现：{{ negative_prompt }}""",
    ),
    "scene_image_front": (
        "场景图片提示词",
        "高质量场景定景",
        ASSET_VARS,
        """{{ style_pack }}

[交付物]
竖屏短剧场景定景图：空间层次清楚，可直接作为该场景的视觉基准。

[参考图角色]
{{ reference_block }}

[空间与细节]
{{ description }}
- 镜头方向：正面；画面正中为场景主体区域，前中后景分明
- 光源方向明确，环境氛围自然（雾、雨丝、光斑、尘埃等按需出现）
- 空间尺度合理，建筑与陈设结构正确，透视不畸变
- 为演员留出可站立的表演空间，地面与墙面材质细节清楚

[Constraints]
- 保持空间结构、主要陈设位置与光照方向不变
- 不出现人物正脸特写或人体轮廓
""" + NO_TEXT_CONSTRAINTS + """
- 避免出现：{{ negative_prompt }}""",
    ),
    "scene_image_other": (
        "场景侧面/后面图片提示词",
        "同一场景的其他机位",
        ASSET_VARS,
        """{{ style_pack }}

[交付物]
同一场景的{{ view_angle }}机位定景图：空间结构自洽。

[参考图角色]
{{ reference_block }}

[空间与细节]
仅修改：观察方向切换为{{ view_angle }}；同一空间内的另一个机位。
保留：墙、地面、门窗与陈设的相对位置，光源方向、色温与氛围。
{{ description }}
- 不出现与正面图矛盾的结构，不新增主要陈设
- 透视与空间尺度保持一致

[Constraints]
- 与正面定景画面完全同一场景
- 不出现人物正脸特写或人体轮廓
""" + NO_TEXT_CONSTRAINTS + """
- 避免出现：{{ negative_prompt }}""",
    ),
    "costume_image_front": (
        "服装图片提示词",
        "高质量服装呈现",
        ASSET_VARS,
        """{{ style_pack }}

[交付物]
服装整体呈现图：完整全身穿着，简洁中性背景，服装占画面三分之二以上。

[参考图角色]
{{ reference_block }}

[主体与细节]
{{ description }}
- 版型与剪裁交代清楚
- 布料纹理、车线、钮扣、拉链、金属配件与褶皱细节清晰可见
- 柔和的正面主光加侧向补光，服装颜色还原准确，无偏色
- 不出现人物面部特写分散注意力

[Constraints]
- 保持服装的版型、颜色、材质与细节不变
""" + NO_TEXT_CONSTRAINTS + """
- 避免出现：{{ negative_prompt }}""",
    ),
    "costume_image_other": (
        "服装侧面/后面图片提示词",
        "同一套服装的其他视角",
        ASSET_VARS,
        """{{ style_pack }}

[交付物]
同一套服装的{{ view_angle }}呈现图。

[参考图角色]
{{ reference_block }}

[主体与细节]
仅修改：视角为{{ view_angle }}；只呈现该视角应有的信息，不残留正面特征。
保留：版型、颜色、材质、接缝、开衩与配饰位置。
{{ description }}
- 同一件衣服的侧面/背面结构合理
- 光线与背景承接正面图，布料质感与颜色保持一致

[Constraints]
- 与正面服装图完全同一套服装
""" + NO_TEXT_CONSTRAINTS + """
- 避免出现：{{ negative_prompt }}""",
    ),
    "combined": (
        "通用兜底图片提示词",
        "无专用类别时的通用画面模板",
        ASSET_VARS,
        """{{ style_pack }}

[交付物]
高质量{{ visual_style }}画面主体：主体明确、构图稳定。

[参考图角色]
{{ reference_block }}

[主体与细节]
{{ description }}
- 主体占画面主要面积，空间层次与光线方向清楚
- 材质、纹理与颜色表现到位

[Constraints]
- 保持已确认的主体身份、服装与空间关系
""" + NO_TEXT_CONSTRAINTS + """
- 避免出现：{{ negative_prompt }}""",
    ),
}

FRAME_TEMPLATES: dict[str, tuple[str, str, list[str], str]] = {
    "frame_head_prompt": (
        "镜头首帧提示词模板",
        "分镜首帧基础提示词（后台可编辑）",
        list(_SHOT_FRAME_INPUT_VARS),
        _FIRST_FRAME_TEMPLATE,
    ),
    "frame_tail_prompt": (
        "镜头尾帧提示词模板",
        "分镜尾帧基础提示词（后台可编辑）",
        list(_SHOT_FRAME_INPUT_VARS),
        _LAST_FRAME_TEMPLATE,
    ),
    "frame_key_prompt": (
        "镜头关键帧提示词模板",
        "分镜关键帧基础提示词（后台可编辑）",
        list(_SHOT_FRAME_INPUT_VARS),
        _KEY_FRAME_TEMPLATE,
    ),
}

ALL_TEMPLATES = {**ASSET_TEMPLATES, **FRAME_TEMPLATES}


def sql_literal(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def build_sql(
    *,
    title: str = "028-rewrite-image-prompt-templates.sql",
    backup_table: str = "",
) -> str:
    lines: list[str] = [
        f"-- {title}",
        "-- 图片提示词模板：交付物 → 参考图角色 → 主体与细节 → 统一约束。",
        "-- 由 backend/scripts/gen_prompt_templates_sql.py 生成，请勿手工编辑。",
        "-- 幂等：已存在同类别则 UPDATE，不存在则 INSERT。",
        "-- 注意：video_prompt 故意不播种 —— 视频提示词走 IR → H3 渲染器。",
        "",
        "SET NAMES utf8mb4;",
        "",
    ]
    if backup_table:
        lines.extend(
            [
                f"-- 部署前备份：保留本次更新前的全部模板内容，便于回滚。",
                f"CREATE TABLE IF NOT EXISTS `{backup_table}` AS SELECT * FROM `prompt_templates`;",
                "",
            ]
        )
    for category, (name, preview, variables, content) in ALL_TEMPLATES.items():
        lines.append(f"-- ===== {category} =====")
        lines.append(
            "UPDATE `prompt_templates` SET "
            f"`name` = {sql_literal(name)}, "
            f"`preview` = {sql_literal(preview)}, "
            f"`content` = {sql_literal(content)}, "
            f"`variables` = CAST({sql_literal(json.dumps(variables, ensure_ascii=False))} AS JSON), "
            "`is_default` = 1, `is_system` = 1, "
            "`updated_at` = NOW() "
            f"WHERE `category` = {sql_literal(category)};"
        )
        lines.append(
            "INSERT INTO `prompt_templates` "
            "(`id`, `category`, `name`, `preview`, `content`, `variables`, `is_default`, `is_system`, `created_at`, `updated_at`) "
            f"SELECT UUID(), {sql_literal(category)}, {sql_literal(name)}, {sql_literal(preview)}, "
            f"{sql_literal(content)}, CAST({sql_literal(json.dumps(variables, ensure_ascii=False))} AS JSON), 1, 1, NOW(), NOW() "
            f"FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM `prompt_templates` WHERE `category` = {sql_literal(category)});"
        )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="028-rewrite-image-prompt-templates.sql",
        help="输出到 backend/sql/ 的文件名",
    )
    parser.add_argument(
        "--title",
        default="028-rewrite-image-prompt-templates.sql",
        help="SQL 文件首行的迁移标题",
    )
    parser.add_argument(
        "--backup-table",
        default="prompt_templates_backup_028",
        help="迁移前备份表名；传空字符串则不生成备份语句",
    )
    args = parser.parse_args()
    out = BACKEND_DIR / "sql" / args.output
    out.write_text(
        build_sql(title=args.title, backup_table=args.backup_table),
        encoding="utf-8",
    )
    print(f"wrote {out} ({len(ALL_TEMPLATES)} categories)")


if __name__ == "__main__":
    main()
