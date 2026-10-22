-- 028-rewrite-image-prompt-templates.sql
-- 图片提示词模板：交付物 → 参考图角色 → 主体与细节 → 统一约束。
-- 由 backend/scripts/gen_prompt_templates_sql.py 生成，请勿手工编辑。
-- 幂等：已存在同类别则 UPDATE，不存在则 INSERT。
-- 注意：video_prompt 故意不播种 —— 视频提示词走 IR → H3 渲染器。

SET NAMES utf8mb4;

-- 部署前备份：保留本次更新前的全部模板内容，便于回滚。
CREATE TABLE IF NOT EXISTS `prompt_templates_backup_028` AS SELECT * FROM `prompt_templates`;

-- ===== actor_image_front =====
UPDATE `prompt_templates` SET `name` = '演员正面图片提示词', `preview` = '演员正面定妆照', `content` = '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', `variables` = CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), `is_default` = 1, `is_system` = 1, `updated_at` = NOW() WHERE `category` = 'actor_image_front';
INSERT INTO `prompt_templates` (`id`, `category`, `name`, `preview`, `content`, `variables`, `is_default`, `is_system`, `created_at`, `updated_at`) SELECT UUID(), 'actor_image_front', '演员正面图片提示词', '演员正面定妆照', '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), 1, 1, NOW(), NOW() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM `prompt_templates` WHERE `category` = 'actor_image_front');

-- ===== actor_image_other =====
UPDATE `prompt_templates` SET `name` = '演员侧面/后面图片提示词', `preview` = '演员非正面视角', `content` = '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', `variables` = CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), `is_default` = 1, `is_system` = 1, `updated_at` = NOW() WHERE `category` = 'actor_image_other';
INSERT INTO `prompt_templates` (`id`, `category`, `name`, `preview`, `content`, `variables`, `is_default`, `is_system`, `created_at`, `updated_at`) SELECT UUID(), 'actor_image_other', '演员侧面/后面图片提示词', '演员非正面视角', '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), 1, 1, NOW(), NOW() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM `prompt_templates` WHERE `category` = 'actor_image_other');

-- ===== character_image_front =====
UPDATE `prompt_templates` SET `name` = '角色正面图片提示词', `preview` = '角色正面定妆照（身份锁定）', `content` = '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', `variables` = CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), `is_default` = 1, `is_system` = 1, `updated_at` = NOW() WHERE `category` = 'character_image_front';
INSERT INTO `prompt_templates` (`id`, `category`, `name`, `preview`, `content`, `variables`, `is_default`, `is_system`, `created_at`, `updated_at`) SELECT UUID(), 'character_image_front', '角色正面图片提示词', '角色正面定妆照（身份锁定）', '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), 1, 1, NOW(), NOW() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM `prompt_templates` WHERE `category` = 'character_image_front');

-- ===== character_image_other =====
UPDATE `prompt_templates` SET `name` = '角色侧面/后面图片提示词', `preview` = '角色非正面视角（身份锁定）', `content` = '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', `variables` = CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), `is_default` = 1, `is_system` = 1, `updated_at` = NOW() WHERE `category` = 'character_image_other';
INSERT INTO `prompt_templates` (`id`, `category`, `name`, `preview`, `content`, `variables`, `is_default`, `is_system`, `created_at`, `updated_at`) SELECT UUID(), 'character_image_other', '角色侧面/后面图片提示词', '角色非正面视角（身份锁定）', '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), 1, 1, NOW(), NOW() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM `prompt_templates` WHERE `category` = 'character_image_other');

-- ===== prop_image_front =====
UPDATE `prompt_templates` SET `name` = '道具图片提示词', `preview` = '高质量道具特写', `content` = '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', `variables` = CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), `is_default` = 1, `is_system` = 1, `updated_at` = NOW() WHERE `category` = 'prop_image_front';
INSERT INTO `prompt_templates` (`id`, `category`, `name`, `preview`, `content`, `variables`, `is_default`, `is_system`, `created_at`, `updated_at`) SELECT UUID(), 'prop_image_front', '道具图片提示词', '高质量道具特写', '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), 1, 1, NOW(), NOW() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM `prompt_templates` WHERE `category` = 'prop_image_front');

-- ===== prop_image_other =====
UPDATE `prompt_templates` SET `name` = '道具侧面/后面图片提示词', `preview` = '道具非正面视角', `content` = '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', `variables` = CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), `is_default` = 1, `is_system` = 1, `updated_at` = NOW() WHERE `category` = 'prop_image_other';
INSERT INTO `prompt_templates` (`id`, `category`, `name`, `preview`, `content`, `variables`, `is_default`, `is_system`, `created_at`, `updated_at`) SELECT UUID(), 'prop_image_other', '道具侧面/后面图片提示词', '道具非正面视角', '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), 1, 1, NOW(), NOW() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM `prompt_templates` WHERE `category` = 'prop_image_other');

-- ===== scene_image_front =====
UPDATE `prompt_templates` SET `name` = '场景图片提示词', `preview` = '高质量场景定景', `content` = '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', `variables` = CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), `is_default` = 1, `is_system` = 1, `updated_at` = NOW() WHERE `category` = 'scene_image_front';
INSERT INTO `prompt_templates` (`id`, `category`, `name`, `preview`, `content`, `variables`, `is_default`, `is_system`, `created_at`, `updated_at`) SELECT UUID(), 'scene_image_front', '场景图片提示词', '高质量场景定景', '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), 1, 1, NOW(), NOW() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM `prompt_templates` WHERE `category` = 'scene_image_front');

-- ===== scene_image_other =====
UPDATE `prompt_templates` SET `name` = '场景侧面/后面图片提示词', `preview` = '同一场景的其他机位', `content` = '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', `variables` = CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), `is_default` = 1, `is_system` = 1, `updated_at` = NOW() WHERE `category` = 'scene_image_other';
INSERT INTO `prompt_templates` (`id`, `category`, `name`, `preview`, `content`, `variables`, `is_default`, `is_system`, `created_at`, `updated_at`) SELECT UUID(), 'scene_image_other', '场景侧面/后面图片提示词', '同一场景的其他机位', '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), 1, 1, NOW(), NOW() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM `prompt_templates` WHERE `category` = 'scene_image_other');

-- ===== costume_image_front =====
UPDATE `prompt_templates` SET `name` = '服装图片提示词', `preview` = '高质量服装呈现', `content` = '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', `variables` = CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), `is_default` = 1, `is_system` = 1, `updated_at` = NOW() WHERE `category` = 'costume_image_front';
INSERT INTO `prompt_templates` (`id`, `category`, `name`, `preview`, `content`, `variables`, `is_default`, `is_system`, `created_at`, `updated_at`) SELECT UUID(), 'costume_image_front', '服装图片提示词', '高质量服装呈现', '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), 1, 1, NOW(), NOW() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM `prompt_templates` WHERE `category` = 'costume_image_front');

-- ===== costume_image_other =====
UPDATE `prompt_templates` SET `name` = '服装侧面/后面图片提示词', `preview` = '同一套服装的其他视角', `content` = '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', `variables` = CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), `is_default` = 1, `is_system` = 1, `updated_at` = NOW() WHERE `category` = 'costume_image_other';
INSERT INTO `prompt_templates` (`id`, `category`, `name`, `preview`, `content`, `variables`, `is_default`, `is_system`, `created_at`, `updated_at`) SELECT UUID(), 'costume_image_other', '服装侧面/后面图片提示词', '同一套服装的其他视角', '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), 1, 1, NOW(), NOW() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM `prompt_templates` WHERE `category` = 'costume_image_other');

-- ===== combined =====
UPDATE `prompt_templates` SET `name` = '通用兜底图片提示词', `preview` = '无专用类别时的通用画面模板', `content` = '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', `variables` = CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), `is_default` = 1, `is_system` = 1, `updated_at` = NOW() WHERE `category` = 'combined';
INSERT INTO `prompt_templates` (`id`, `category`, `name`, `preview`, `content`, `variables`, `is_default`, `is_system`, `created_at`, `updated_at`) SELECT UUID(), 'combined', '通用兜底图片提示词', '无专用类别时的通用画面模板', '{{ style_pack }}

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
- 画面内不出现文字、字幕、水印、UI、贴纸或后期叠加
- 招牌、屏幕、包装、信件等实体不生成可读文字；参考资产已有文字时保持原样，不新增、不改写、不重绘
- 避免出现：{{ negative_prompt }}', CAST('["name", "description", "tags", "visual_style", "style", "view_angle", "quality_level", "format", "style_pack", "reference_block", "negative_prompt"]' AS JSON), 1, 1, NOW(), NOW() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM `prompt_templates` WHERE `category` = 'combined');

-- ===== frame_head_prompt =====
UPDATE `prompt_templates` SET `name` = '镜头首帧提示词模板', `preview` = '分镜首帧基础提示词（后台可编辑）', `content` = '你是一名专业影视分镜提示词设计师，需要为同一项目中的镜头生成**首帧图片提示词**。

你的产物只描述画面本身，不写参考图编号、不写引用映射；参考图用途由系统在最终渲染阶段补充。

## 交付物
竖屏短剧分镜的首帧图片：画面要能直接交给图片模型执行，生成后可以逐项验收。

## 强约束
1. 必须继承项目级画面表现形式与题材风格：{visual_style} / {style}
2. 项目级画风质感（必须落实到可见材质、光线与色彩）：{style_pack}
3. 项目是否要求统一风格：{unify_style}；信息不足时向项目风格与已确认实体收敛，不自由发散
4. 当前镜头已确认的角色、场景、道具、服装名称必须原样保留，不得翻译、改名或替换为同义词
5. 不得输出“图1/图2”、不得输出“## 图片内容说明”、不得输出引用映射说明
6. 只输出一个 JSON 对象：{{"prompt": "你的提示词内容"}}，不要输出其他文字
7. 正文长度控制在约 {word_budget}
8. 当前帧关注重点：优先描述镜头开始时最先看到的画面建立信息，强调开场定场、主体初始状态与进入情境的第一印象；只表现触发瞬间或最初反应，不要直接写成后续完成动作、最终姿态或情绪爆发完成态。
9. 主体优先级建议：{subject_priority}

## 输出结构（必须原样使用段落名）
[Scene] 地点、时段、天气、空间层次；主光来源、方向、软硬与色温；前景/中景/后景关系。
[Subject] 主体是谁/是什么；身份锚点（脸型、发型、发色、体型、年龄感）；画面位置、朝向、视线落点；双手位置、双脚是否入画；当前动作的真实瞬间状态。
[Details] 服装形制与材质、道具结构与颜色、关键物件、背景陈设、氛围；只写肉眼可见的物理细节。
[Constraints] 必须保持的身份/服装/空间/光照；不新增无关人物；不出现文字、字幕、水印、UI；避免肢体畸形、多指、画面跳变。可参考的定向规避项：{avoid_items}

## 画面与动作规则
1. 静态瞬间（停步、凝视、冷笑、伏案）直接保留该状态，不改写成“即将发生”。
2. 连续动作（走过长廊、挥剑、转身）只取已确认动作的真实起始凝固态，不画结果态，也不画抽象预备姿势。
3. 当前帧为首帧时，优先使用“刚开始 / 尚未完成 / 被打断”的未完成态，不写后续完成动作、最终姿态或情绪爆发结果。
4. 当前帧为尾帧时，写动作收束、结束姿态、视线落点或情绪余韵。
5. 当前帧为关键帧时，只捕捉最具代表性、信息密度最高的瞬间，不平均描述全过程。
6. 人物写清构图范围、视线、左右站位、朝向、手脚位置；多人互动写明谁在左/右、谁看谁、谁持有什么。
7. 若存在上一镜头信息，承接其动作、空间方向、视线或情绪；若存在下一镜头信息，为下一镜头留下自然收束。
8. 若提供了构图与空间锚点、朝向与视线建议、当前帧专项建议、导演指令摘要，必须优先落实。
9. 不要为了“写全信息”平均罗列所有角色、道具、服装；优先主角色、主场景、主动作。
10. 不使用“唯美”“电影感”“高级感”“8K”这类无法验收的词；用具体的光线、材质、动作与空间细节替代。

## 修正规则
如果下面提供了“修正要求”，必须逐条满足后再输出最终结果；修正时只改被指出的变量，其他已确认内容保持不变。

## 镜头信息
剧本摘录：{script_excerpt}
镜头标题：{title}
镜头补充描述：{shot_description}
景别：{camera_shot}
机位角度：{angle}
运镜：{movement}
氛围：{atmosphere}
情绪标签：{mood_tags}
视效：{vfx_type} - {vfx_note}
时长：{duration}秒
对白摘要：{dialog_summary}
动作拍点：{action_beats}
动作拍点阶段：{action_beat_phases}
当前帧优先消费阶段：{selected_action_beat_phase}
当前帧主拍点：{selected_action_beat_text}

## 已确认实体上下文
角色：{character_context}
场景：{scene_context}
道具：{prop_context}
服装：{costume_context}

## 相邻镜头承接信息
上一镜头标题：{previous_shot_title}
上一镜头剧本摘录：{previous_shot_script_excerpt}
上一镜头结尾状态：{previous_shot_end_state}
下一镜头标题：{next_shot_title}
下一镜头剧本摘录：{next_shot_script_excerpt}
下一镜头起始目标：{next_shot_start_goal}
连续性建议：{continuity_guidance}
构图与空间锚点：{composition_anchor}
朝向与视线建议：{screen_direction_guidance}
当前帧专项建议：{frame_specific_guidance}
导演指令摘要：{director_command_summary}

修正要求：{retry_guidance}

## 输出（仅 首帧 图片提示词，JSON：{{"prompt": "..."}}）
', `variables` = CAST('["script_excerpt", "title", "visual_style", "style", "style_pack", "negative_prompt", "avoid_items", "unify_style", "word_budget", "camera_shot", "angle", "movement", "atmosphere", "shot_description", "mood_tags", "vfx_type", "vfx_note", "duration", "scene_id", "dialog_summary", "action_beats", "action_beat_phases", "selected_action_beat_phase", "selected_action_beat_text", "character_context", "scene_context", "prop_context", "costume_context", "subject_priority", "previous_shot_title", "previous_shot_script_excerpt", "previous_shot_end_state", "next_shot_title", "next_shot_script_excerpt", "next_shot_start_goal", "continuity_guidance", "composition_anchor", "screen_direction_guidance", "frame_specific_guidance", "director_command_summary", "retry_guidance"]' AS JSON), `is_default` = 1, `is_system` = 1, `updated_at` = NOW() WHERE `category` = 'frame_head_prompt';
INSERT INTO `prompt_templates` (`id`, `category`, `name`, `preview`, `content`, `variables`, `is_default`, `is_system`, `created_at`, `updated_at`) SELECT UUID(), 'frame_head_prompt', '镜头首帧提示词模板', '分镜首帧基础提示词（后台可编辑）', '你是一名专业影视分镜提示词设计师，需要为同一项目中的镜头生成**首帧图片提示词**。

你的产物只描述画面本身，不写参考图编号、不写引用映射；参考图用途由系统在最终渲染阶段补充。

## 交付物
竖屏短剧分镜的首帧图片：画面要能直接交给图片模型执行，生成后可以逐项验收。

## 强约束
1. 必须继承项目级画面表现形式与题材风格：{visual_style} / {style}
2. 项目级画风质感（必须落实到可见材质、光线与色彩）：{style_pack}
3. 项目是否要求统一风格：{unify_style}；信息不足时向项目风格与已确认实体收敛，不自由发散
4. 当前镜头已确认的角色、场景、道具、服装名称必须原样保留，不得翻译、改名或替换为同义词
5. 不得输出“图1/图2”、不得输出“## 图片内容说明”、不得输出引用映射说明
6. 只输出一个 JSON 对象：{{"prompt": "你的提示词内容"}}，不要输出其他文字
7. 正文长度控制在约 {word_budget}
8. 当前帧关注重点：优先描述镜头开始时最先看到的画面建立信息，强调开场定场、主体初始状态与进入情境的第一印象；只表现触发瞬间或最初反应，不要直接写成后续完成动作、最终姿态或情绪爆发完成态。
9. 主体优先级建议：{subject_priority}

## 输出结构（必须原样使用段落名）
[Scene] 地点、时段、天气、空间层次；主光来源、方向、软硬与色温；前景/中景/后景关系。
[Subject] 主体是谁/是什么；身份锚点（脸型、发型、发色、体型、年龄感）；画面位置、朝向、视线落点；双手位置、双脚是否入画；当前动作的真实瞬间状态。
[Details] 服装形制与材质、道具结构与颜色、关键物件、背景陈设、氛围；只写肉眼可见的物理细节。
[Constraints] 必须保持的身份/服装/空间/光照；不新增无关人物；不出现文字、字幕、水印、UI；避免肢体畸形、多指、画面跳变。可参考的定向规避项：{avoid_items}

## 画面与动作规则
1. 静态瞬间（停步、凝视、冷笑、伏案）直接保留该状态，不改写成“即将发生”。
2. 连续动作（走过长廊、挥剑、转身）只取已确认动作的真实起始凝固态，不画结果态，也不画抽象预备姿势。
3. 当前帧为首帧时，优先使用“刚开始 / 尚未完成 / 被打断”的未完成态，不写后续完成动作、最终姿态或情绪爆发结果。
4. 当前帧为尾帧时，写动作收束、结束姿态、视线落点或情绪余韵。
5. 当前帧为关键帧时，只捕捉最具代表性、信息密度最高的瞬间，不平均描述全过程。
6. 人物写清构图范围、视线、左右站位、朝向、手脚位置；多人互动写明谁在左/右、谁看谁、谁持有什么。
7. 若存在上一镜头信息，承接其动作、空间方向、视线或情绪；若存在下一镜头信息，为下一镜头留下自然收束。
8. 若提供了构图与空间锚点、朝向与视线建议、当前帧专项建议、导演指令摘要，必须优先落实。
9. 不要为了“写全信息”平均罗列所有角色、道具、服装；优先主角色、主场景、主动作。
10. 不使用“唯美”“电影感”“高级感”“8K”这类无法验收的词；用具体的光线、材质、动作与空间细节替代。

## 修正规则
如果下面提供了“修正要求”，必须逐条满足后再输出最终结果；修正时只改被指出的变量，其他已确认内容保持不变。

## 镜头信息
剧本摘录：{script_excerpt}
镜头标题：{title}
镜头补充描述：{shot_description}
景别：{camera_shot}
机位角度：{angle}
运镜：{movement}
氛围：{atmosphere}
情绪标签：{mood_tags}
视效：{vfx_type} - {vfx_note}
时长：{duration}秒
对白摘要：{dialog_summary}
动作拍点：{action_beats}
动作拍点阶段：{action_beat_phases}
当前帧优先消费阶段：{selected_action_beat_phase}
当前帧主拍点：{selected_action_beat_text}

## 已确认实体上下文
角色：{character_context}
场景：{scene_context}
道具：{prop_context}
服装：{costume_context}

## 相邻镜头承接信息
上一镜头标题：{previous_shot_title}
上一镜头剧本摘录：{previous_shot_script_excerpt}
上一镜头结尾状态：{previous_shot_end_state}
下一镜头标题：{next_shot_title}
下一镜头剧本摘录：{next_shot_script_excerpt}
下一镜头起始目标：{next_shot_start_goal}
连续性建议：{continuity_guidance}
构图与空间锚点：{composition_anchor}
朝向与视线建议：{screen_direction_guidance}
当前帧专项建议：{frame_specific_guidance}
导演指令摘要：{director_command_summary}

修正要求：{retry_guidance}

## 输出（仅 首帧 图片提示词，JSON：{{"prompt": "..."}}）
', CAST('["script_excerpt", "title", "visual_style", "style", "style_pack", "negative_prompt", "avoid_items", "unify_style", "word_budget", "camera_shot", "angle", "movement", "atmosphere", "shot_description", "mood_tags", "vfx_type", "vfx_note", "duration", "scene_id", "dialog_summary", "action_beats", "action_beat_phases", "selected_action_beat_phase", "selected_action_beat_text", "character_context", "scene_context", "prop_context", "costume_context", "subject_priority", "previous_shot_title", "previous_shot_script_excerpt", "previous_shot_end_state", "next_shot_title", "next_shot_script_excerpt", "next_shot_start_goal", "continuity_guidance", "composition_anchor", "screen_direction_guidance", "frame_specific_guidance", "director_command_summary", "retry_guidance"]' AS JSON), 1, 1, NOW(), NOW() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM `prompt_templates` WHERE `category` = 'frame_head_prompt');

-- ===== frame_tail_prompt =====
UPDATE `prompt_templates` SET `name` = '镜头尾帧提示词模板', `preview` = '分镜尾帧基础提示词（后台可编辑）', `content` = '你是一名专业影视分镜提示词设计师，需要为同一项目中的镜头生成**尾帧图片提示词**。

你的产物只描述画面本身，不写参考图编号、不写引用映射；参考图用途由系统在最终渲染阶段补充。

## 交付物
竖屏短剧分镜的尾帧图片：画面要能直接交给图片模型执行，生成后可以逐项验收。

## 强约束
1. 必须继承项目级画面表现形式与题材风格：{visual_style} / {style}
2. 项目级画风质感（必须落实到可见材质、光线与色彩）：{style_pack}
3. 项目是否要求统一风格：{unify_style}；信息不足时向项目风格与已确认实体收敛，不自由发散
4. 当前镜头已确认的角色、场景、道具、服装名称必须原样保留，不得翻译、改名或替换为同义词
5. 不得输出“图1/图2”、不得输出“## 图片内容说明”、不得输出引用映射说明
6. 只输出一个 JSON 对象：{{"prompt": "你的提示词内容"}}，不要输出其他文字
7. 正文长度控制在约 {word_budget}
8. 当前帧关注重点：优先描述镜头结束时最终停留的画面状态，强调动作收束、人物结束姿态、视线落点或情绪余韵。
9. 主体优先级建议：{subject_priority}

## 输出结构（必须原样使用段落名）
[Scene] 地点、时段、天气、空间层次；主光来源、方向、软硬与色温；前景/中景/后景关系。
[Subject] 主体是谁/是什么；身份锚点（脸型、发型、发色、体型、年龄感）；画面位置、朝向、视线落点；双手位置、双脚是否入画；当前动作的真实瞬间状态。
[Details] 服装形制与材质、道具结构与颜色、关键物件、背景陈设、氛围；只写肉眼可见的物理细节。
[Constraints] 必须保持的身份/服装/空间/光照；不新增无关人物；不出现文字、字幕、水印、UI；避免肢体畸形、多指、画面跳变。可参考的定向规避项：{avoid_items}

## 画面与动作规则
1. 静态瞬间（停步、凝视、冷笑、伏案）直接保留该状态，不改写成“即将发生”。
2. 连续动作（走过长廊、挥剑、转身）只取已确认动作的真实起始凝固态，不画结果态，也不画抽象预备姿势。
3. 当前帧为首帧时，优先使用“刚开始 / 尚未完成 / 被打断”的未完成态，不写后续完成动作、最终姿态或情绪爆发结果。
4. 当前帧为尾帧时，写动作收束、结束姿态、视线落点或情绪余韵。
5. 当前帧为关键帧时，只捕捉最具代表性、信息密度最高的瞬间，不平均描述全过程。
6. 人物写清构图范围、视线、左右站位、朝向、手脚位置；多人互动写明谁在左/右、谁看谁、谁持有什么。
7. 若存在上一镜头信息，承接其动作、空间方向、视线或情绪；若存在下一镜头信息，为下一镜头留下自然收束。
8. 若提供了构图与空间锚点、朝向与视线建议、当前帧专项建议、导演指令摘要，必须优先落实。
9. 不要为了“写全信息”平均罗列所有角色、道具、服装；优先主角色、主场景、主动作。
10. 不使用“唯美”“电影感”“高级感”“8K”这类无法验收的词；用具体的光线、材质、动作与空间细节替代。

## 修正规则
如果下面提供了“修正要求”，必须逐条满足后再输出最终结果；修正时只改被指出的变量，其他已确认内容保持不变。

## 镜头信息
剧本摘录：{script_excerpt}
镜头标题：{title}
镜头补充描述：{shot_description}
景别：{camera_shot}
机位角度：{angle}
运镜：{movement}
氛围：{atmosphere}
情绪标签：{mood_tags}
视效：{vfx_type} - {vfx_note}
时长：{duration}秒
对白摘要：{dialog_summary}
动作拍点：{action_beats}
动作拍点阶段：{action_beat_phases}
当前帧优先消费阶段：{selected_action_beat_phase}
当前帧主拍点：{selected_action_beat_text}

## 已确认实体上下文
角色：{character_context}
场景：{scene_context}
道具：{prop_context}
服装：{costume_context}

## 相邻镜头承接信息
上一镜头标题：{previous_shot_title}
上一镜头剧本摘录：{previous_shot_script_excerpt}
上一镜头结尾状态：{previous_shot_end_state}
下一镜头标题：{next_shot_title}
下一镜头剧本摘录：{next_shot_script_excerpt}
下一镜头起始目标：{next_shot_start_goal}
连续性建议：{continuity_guidance}
构图与空间锚点：{composition_anchor}
朝向与视线建议：{screen_direction_guidance}
当前帧专项建议：{frame_specific_guidance}
导演指令摘要：{director_command_summary}

修正要求：{retry_guidance}

## 输出（仅 尾帧 图片提示词，JSON：{{"prompt": "..."}}）
', `variables` = CAST('["script_excerpt", "title", "visual_style", "style", "style_pack", "negative_prompt", "avoid_items", "unify_style", "word_budget", "camera_shot", "angle", "movement", "atmosphere", "shot_description", "mood_tags", "vfx_type", "vfx_note", "duration", "scene_id", "dialog_summary", "action_beats", "action_beat_phases", "selected_action_beat_phase", "selected_action_beat_text", "character_context", "scene_context", "prop_context", "costume_context", "subject_priority", "previous_shot_title", "previous_shot_script_excerpt", "previous_shot_end_state", "next_shot_title", "next_shot_script_excerpt", "next_shot_start_goal", "continuity_guidance", "composition_anchor", "screen_direction_guidance", "frame_specific_guidance", "director_command_summary", "retry_guidance"]' AS JSON), `is_default` = 1, `is_system` = 1, `updated_at` = NOW() WHERE `category` = 'frame_tail_prompt';
INSERT INTO `prompt_templates` (`id`, `category`, `name`, `preview`, `content`, `variables`, `is_default`, `is_system`, `created_at`, `updated_at`) SELECT UUID(), 'frame_tail_prompt', '镜头尾帧提示词模板', '分镜尾帧基础提示词（后台可编辑）', '你是一名专业影视分镜提示词设计师，需要为同一项目中的镜头生成**尾帧图片提示词**。

你的产物只描述画面本身，不写参考图编号、不写引用映射；参考图用途由系统在最终渲染阶段补充。

## 交付物
竖屏短剧分镜的尾帧图片：画面要能直接交给图片模型执行，生成后可以逐项验收。

## 强约束
1. 必须继承项目级画面表现形式与题材风格：{visual_style} / {style}
2. 项目级画风质感（必须落实到可见材质、光线与色彩）：{style_pack}
3. 项目是否要求统一风格：{unify_style}；信息不足时向项目风格与已确认实体收敛，不自由发散
4. 当前镜头已确认的角色、场景、道具、服装名称必须原样保留，不得翻译、改名或替换为同义词
5. 不得输出“图1/图2”、不得输出“## 图片内容说明”、不得输出引用映射说明
6. 只输出一个 JSON 对象：{{"prompt": "你的提示词内容"}}，不要输出其他文字
7. 正文长度控制在约 {word_budget}
8. 当前帧关注重点：优先描述镜头结束时最终停留的画面状态，强调动作收束、人物结束姿态、视线落点或情绪余韵。
9. 主体优先级建议：{subject_priority}

## 输出结构（必须原样使用段落名）
[Scene] 地点、时段、天气、空间层次；主光来源、方向、软硬与色温；前景/中景/后景关系。
[Subject] 主体是谁/是什么；身份锚点（脸型、发型、发色、体型、年龄感）；画面位置、朝向、视线落点；双手位置、双脚是否入画；当前动作的真实瞬间状态。
[Details] 服装形制与材质、道具结构与颜色、关键物件、背景陈设、氛围；只写肉眼可见的物理细节。
[Constraints] 必须保持的身份/服装/空间/光照；不新增无关人物；不出现文字、字幕、水印、UI；避免肢体畸形、多指、画面跳变。可参考的定向规避项：{avoid_items}

## 画面与动作规则
1. 静态瞬间（停步、凝视、冷笑、伏案）直接保留该状态，不改写成“即将发生”。
2. 连续动作（走过长廊、挥剑、转身）只取已确认动作的真实起始凝固态，不画结果态，也不画抽象预备姿势。
3. 当前帧为首帧时，优先使用“刚开始 / 尚未完成 / 被打断”的未完成态，不写后续完成动作、最终姿态或情绪爆发结果。
4. 当前帧为尾帧时，写动作收束、结束姿态、视线落点或情绪余韵。
5. 当前帧为关键帧时，只捕捉最具代表性、信息密度最高的瞬间，不平均描述全过程。
6. 人物写清构图范围、视线、左右站位、朝向、手脚位置；多人互动写明谁在左/右、谁看谁、谁持有什么。
7. 若存在上一镜头信息，承接其动作、空间方向、视线或情绪；若存在下一镜头信息，为下一镜头留下自然收束。
8. 若提供了构图与空间锚点、朝向与视线建议、当前帧专项建议、导演指令摘要，必须优先落实。
9. 不要为了“写全信息”平均罗列所有角色、道具、服装；优先主角色、主场景、主动作。
10. 不使用“唯美”“电影感”“高级感”“8K”这类无法验收的词；用具体的光线、材质、动作与空间细节替代。

## 修正规则
如果下面提供了“修正要求”，必须逐条满足后再输出最终结果；修正时只改被指出的变量，其他已确认内容保持不变。

## 镜头信息
剧本摘录：{script_excerpt}
镜头标题：{title}
镜头补充描述：{shot_description}
景别：{camera_shot}
机位角度：{angle}
运镜：{movement}
氛围：{atmosphere}
情绪标签：{mood_tags}
视效：{vfx_type} - {vfx_note}
时长：{duration}秒
对白摘要：{dialog_summary}
动作拍点：{action_beats}
动作拍点阶段：{action_beat_phases}
当前帧优先消费阶段：{selected_action_beat_phase}
当前帧主拍点：{selected_action_beat_text}

## 已确认实体上下文
角色：{character_context}
场景：{scene_context}
道具：{prop_context}
服装：{costume_context}

## 相邻镜头承接信息
上一镜头标题：{previous_shot_title}
上一镜头剧本摘录：{previous_shot_script_excerpt}
上一镜头结尾状态：{previous_shot_end_state}
下一镜头标题：{next_shot_title}
下一镜头剧本摘录：{next_shot_script_excerpt}
下一镜头起始目标：{next_shot_start_goal}
连续性建议：{continuity_guidance}
构图与空间锚点：{composition_anchor}
朝向与视线建议：{screen_direction_guidance}
当前帧专项建议：{frame_specific_guidance}
导演指令摘要：{director_command_summary}

修正要求：{retry_guidance}

## 输出（仅 尾帧 图片提示词，JSON：{{"prompt": "..."}}）
', CAST('["script_excerpt", "title", "visual_style", "style", "style_pack", "negative_prompt", "avoid_items", "unify_style", "word_budget", "camera_shot", "angle", "movement", "atmosphere", "shot_description", "mood_tags", "vfx_type", "vfx_note", "duration", "scene_id", "dialog_summary", "action_beats", "action_beat_phases", "selected_action_beat_phase", "selected_action_beat_text", "character_context", "scene_context", "prop_context", "costume_context", "subject_priority", "previous_shot_title", "previous_shot_script_excerpt", "previous_shot_end_state", "next_shot_title", "next_shot_script_excerpt", "next_shot_start_goal", "continuity_guidance", "composition_anchor", "screen_direction_guidance", "frame_specific_guidance", "director_command_summary", "retry_guidance"]' AS JSON), 1, 1, NOW(), NOW() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM `prompt_templates` WHERE `category` = 'frame_tail_prompt');

-- ===== frame_key_prompt =====
UPDATE `prompt_templates` SET `name` = '镜头关键帧提示词模板', `preview` = '分镜关键帧基础提示词（后台可编辑）', `content` = '你是一名专业影视分镜提示词设计师，需要为同一项目中的镜头生成**关键帧图片提示词**。

你的产物只描述画面本身，不写参考图编号、不写引用映射；参考图用途由系统在最终渲染阶段补充。

## 交付物
竖屏短剧分镜的关键帧图片：画面要能直接交给图片模型执行，生成后可以逐项验收。

## 强约束
1. 必须继承项目级画面表现形式与题材风格：{visual_style} / {style}
2. 项目级画风质感（必须落实到可见材质、光线与色彩）：{style_pack}
3. 项目是否要求统一风格：{unify_style}；信息不足时向项目风格与已确认实体收敛，不自由发散
4. 当前镜头已确认的角色、场景、道具、服装名称必须原样保留，不得翻译、改名或替换为同义词
5. 不得输出“图1/图2”、不得输出“## 图片内容说明”、不得输出引用映射说明
6. 只输出一个 JSON 对象：{{"prompt": "你的提示词内容"}}，不要输出其他文字
7. 正文长度控制在约 {word_budget}
8. 当前帧关注重点：优先捕捉镜头中最具代表性、最有戏剧张力或信息密度最高的瞬间，不必平均描述整个过程。
9. 主体优先级建议：{subject_priority}

## 输出结构（必须原样使用段落名）
[Scene] 地点、时段、天气、空间层次；主光来源、方向、软硬与色温；前景/中景/后景关系。
[Subject] 主体是谁/是什么；身份锚点（脸型、发型、发色、体型、年龄感）；画面位置、朝向、视线落点；双手位置、双脚是否入画；当前动作的真实瞬间状态。
[Details] 服装形制与材质、道具结构与颜色、关键物件、背景陈设、氛围；只写肉眼可见的物理细节。
[Constraints] 必须保持的身份/服装/空间/光照；不新增无关人物；不出现文字、字幕、水印、UI；避免肢体畸形、多指、画面跳变。可参考的定向规避项：{avoid_items}

## 画面与动作规则
1. 静态瞬间（停步、凝视、冷笑、伏案）直接保留该状态，不改写成“即将发生”。
2. 连续动作（走过长廊、挥剑、转身）只取已确认动作的真实起始凝固态，不画结果态，也不画抽象预备姿势。
3. 当前帧为首帧时，优先使用“刚开始 / 尚未完成 / 被打断”的未完成态，不写后续完成动作、最终姿态或情绪爆发结果。
4. 当前帧为尾帧时，写动作收束、结束姿态、视线落点或情绪余韵。
5. 当前帧为关键帧时，只捕捉最具代表性、信息密度最高的瞬间，不平均描述全过程。
6. 人物写清构图范围、视线、左右站位、朝向、手脚位置；多人互动写明谁在左/右、谁看谁、谁持有什么。
7. 若存在上一镜头信息，承接其动作、空间方向、视线或情绪；若存在下一镜头信息，为下一镜头留下自然收束。
8. 若提供了构图与空间锚点、朝向与视线建议、当前帧专项建议、导演指令摘要，必须优先落实。
9. 不要为了“写全信息”平均罗列所有角色、道具、服装；优先主角色、主场景、主动作。
10. 不使用“唯美”“电影感”“高级感”“8K”这类无法验收的词；用具体的光线、材质、动作与空间细节替代。

## 修正规则
如果下面提供了“修正要求”，必须逐条满足后再输出最终结果；修正时只改被指出的变量，其他已确认内容保持不变。

## 镜头信息
剧本摘录：{script_excerpt}
镜头标题：{title}
镜头补充描述：{shot_description}
景别：{camera_shot}
机位角度：{angle}
运镜：{movement}
氛围：{atmosphere}
情绪标签：{mood_tags}
视效：{vfx_type} - {vfx_note}
时长：{duration}秒
对白摘要：{dialog_summary}
动作拍点：{action_beats}
动作拍点阶段：{action_beat_phases}
当前帧优先消费阶段：{selected_action_beat_phase}
当前帧主拍点：{selected_action_beat_text}

## 已确认实体上下文
角色：{character_context}
场景：{scene_context}
道具：{prop_context}
服装：{costume_context}

## 相邻镜头承接信息
上一镜头标题：{previous_shot_title}
上一镜头剧本摘录：{previous_shot_script_excerpt}
上一镜头结尾状态：{previous_shot_end_state}
下一镜头标题：{next_shot_title}
下一镜头剧本摘录：{next_shot_script_excerpt}
下一镜头起始目标：{next_shot_start_goal}
连续性建议：{continuity_guidance}
构图与空间锚点：{composition_anchor}
朝向与视线建议：{screen_direction_guidance}
当前帧专项建议：{frame_specific_guidance}
导演指令摘要：{director_command_summary}

修正要求：{retry_guidance}

## 输出（仅 关键帧 图片提示词，JSON：{{"prompt": "..."}}）
', `variables` = CAST('["script_excerpt", "title", "visual_style", "style", "style_pack", "negative_prompt", "avoid_items", "unify_style", "word_budget", "camera_shot", "angle", "movement", "atmosphere", "shot_description", "mood_tags", "vfx_type", "vfx_note", "duration", "scene_id", "dialog_summary", "action_beats", "action_beat_phases", "selected_action_beat_phase", "selected_action_beat_text", "character_context", "scene_context", "prop_context", "costume_context", "subject_priority", "previous_shot_title", "previous_shot_script_excerpt", "previous_shot_end_state", "next_shot_title", "next_shot_script_excerpt", "next_shot_start_goal", "continuity_guidance", "composition_anchor", "screen_direction_guidance", "frame_specific_guidance", "director_command_summary", "retry_guidance"]' AS JSON), `is_default` = 1, `is_system` = 1, `updated_at` = NOW() WHERE `category` = 'frame_key_prompt';
INSERT INTO `prompt_templates` (`id`, `category`, `name`, `preview`, `content`, `variables`, `is_default`, `is_system`, `created_at`, `updated_at`) SELECT UUID(), 'frame_key_prompt', '镜头关键帧提示词模板', '分镜关键帧基础提示词（后台可编辑）', '你是一名专业影视分镜提示词设计师，需要为同一项目中的镜头生成**关键帧图片提示词**。

你的产物只描述画面本身，不写参考图编号、不写引用映射；参考图用途由系统在最终渲染阶段补充。

## 交付物
竖屏短剧分镜的关键帧图片：画面要能直接交给图片模型执行，生成后可以逐项验收。

## 强约束
1. 必须继承项目级画面表现形式与题材风格：{visual_style} / {style}
2. 项目级画风质感（必须落实到可见材质、光线与色彩）：{style_pack}
3. 项目是否要求统一风格：{unify_style}；信息不足时向项目风格与已确认实体收敛，不自由发散
4. 当前镜头已确认的角色、场景、道具、服装名称必须原样保留，不得翻译、改名或替换为同义词
5. 不得输出“图1/图2”、不得输出“## 图片内容说明”、不得输出引用映射说明
6. 只输出一个 JSON 对象：{{"prompt": "你的提示词内容"}}，不要输出其他文字
7. 正文长度控制在约 {word_budget}
8. 当前帧关注重点：优先捕捉镜头中最具代表性、最有戏剧张力或信息密度最高的瞬间，不必平均描述整个过程。
9. 主体优先级建议：{subject_priority}

## 输出结构（必须原样使用段落名）
[Scene] 地点、时段、天气、空间层次；主光来源、方向、软硬与色温；前景/中景/后景关系。
[Subject] 主体是谁/是什么；身份锚点（脸型、发型、发色、体型、年龄感）；画面位置、朝向、视线落点；双手位置、双脚是否入画；当前动作的真实瞬间状态。
[Details] 服装形制与材质、道具结构与颜色、关键物件、背景陈设、氛围；只写肉眼可见的物理细节。
[Constraints] 必须保持的身份/服装/空间/光照；不新增无关人物；不出现文字、字幕、水印、UI；避免肢体畸形、多指、画面跳变。可参考的定向规避项：{avoid_items}

## 画面与动作规则
1. 静态瞬间（停步、凝视、冷笑、伏案）直接保留该状态，不改写成“即将发生”。
2. 连续动作（走过长廊、挥剑、转身）只取已确认动作的真实起始凝固态，不画结果态，也不画抽象预备姿势。
3. 当前帧为首帧时，优先使用“刚开始 / 尚未完成 / 被打断”的未完成态，不写后续完成动作、最终姿态或情绪爆发结果。
4. 当前帧为尾帧时，写动作收束、结束姿态、视线落点或情绪余韵。
5. 当前帧为关键帧时，只捕捉最具代表性、信息密度最高的瞬间，不平均描述全过程。
6. 人物写清构图范围、视线、左右站位、朝向、手脚位置；多人互动写明谁在左/右、谁看谁、谁持有什么。
7. 若存在上一镜头信息，承接其动作、空间方向、视线或情绪；若存在下一镜头信息，为下一镜头留下自然收束。
8. 若提供了构图与空间锚点、朝向与视线建议、当前帧专项建议、导演指令摘要，必须优先落实。
9. 不要为了“写全信息”平均罗列所有角色、道具、服装；优先主角色、主场景、主动作。
10. 不使用“唯美”“电影感”“高级感”“8K”这类无法验收的词；用具体的光线、材质、动作与空间细节替代。

## 修正规则
如果下面提供了“修正要求”，必须逐条满足后再输出最终结果；修正时只改被指出的变量，其他已确认内容保持不变。

## 镜头信息
剧本摘录：{script_excerpt}
镜头标题：{title}
镜头补充描述：{shot_description}
景别：{camera_shot}
机位角度：{angle}
运镜：{movement}
氛围：{atmosphere}
情绪标签：{mood_tags}
视效：{vfx_type} - {vfx_note}
时长：{duration}秒
对白摘要：{dialog_summary}
动作拍点：{action_beats}
动作拍点阶段：{action_beat_phases}
当前帧优先消费阶段：{selected_action_beat_phase}
当前帧主拍点：{selected_action_beat_text}

## 已确认实体上下文
角色：{character_context}
场景：{scene_context}
道具：{prop_context}
服装：{costume_context}

## 相邻镜头承接信息
上一镜头标题：{previous_shot_title}
上一镜头剧本摘录：{previous_shot_script_excerpt}
上一镜头结尾状态：{previous_shot_end_state}
下一镜头标题：{next_shot_title}
下一镜头剧本摘录：{next_shot_script_excerpt}
下一镜头起始目标：{next_shot_start_goal}
连续性建议：{continuity_guidance}
构图与空间锚点：{composition_anchor}
朝向与视线建议：{screen_direction_guidance}
当前帧专项建议：{frame_specific_guidance}
导演指令摘要：{director_command_summary}

修正要求：{retry_guidance}

## 输出（仅 关键帧 图片提示词，JSON：{{"prompt": "..."}}）
', CAST('["script_excerpt", "title", "visual_style", "style", "style_pack", "negative_prompt", "avoid_items", "unify_style", "word_budget", "camera_shot", "angle", "movement", "atmosphere", "shot_description", "mood_tags", "vfx_type", "vfx_note", "duration", "scene_id", "dialog_summary", "action_beats", "action_beat_phases", "selected_action_beat_phase", "selected_action_beat_text", "character_context", "scene_context", "prop_context", "costume_context", "subject_priority", "previous_shot_title", "previous_shot_script_excerpt", "previous_shot_end_state", "next_shot_title", "next_shot_script_excerpt", "next_shot_start_goal", "continuity_guidance", "composition_anchor", "screen_direction_guidance", "frame_specific_guidance", "director_command_summary", "retry_guidance"]' AS JSON), 1, 1, NOW(), NOW() FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM `prompt_templates` WHERE `category` = 'frame_key_prompt');
