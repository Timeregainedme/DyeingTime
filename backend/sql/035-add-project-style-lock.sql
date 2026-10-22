-- 035-add-project-style-lock.sql
--
-- P2 / C4：视觉风格参考图、结构化描述、项目级风格快照与锁定。
--
-- 设计要点：
-- 1. `project_styles` 继续作为全局风格目录；新增结构化描述、参考图与样张字段。
-- 2. `project_style_snapshots` 保存锁定时的完整副本（含 prompt_pack），
--    因此后续修改/删除目录项不会改变已锁定项目。
-- 3. 三个内置模板以稳定 ID 幂等插入；存量 7 个风格与其 ID 保持不变。
-- 4. 锁定约束由服务端保证（存在快照即拒绝再次选择/锁定），不依赖前端禁用。
--
-- 回滚：
--   DROP TABLE IF EXISTS project_style_snapshots;
--   ALTER TABLE project_styles
--     DROP COLUMN structured_profile,
--     DROP COLUMN reference_file_ids,
--     DROP COLUMN sample_file_ids,
--     DROP COLUMN analysis_status,
--     DROP COLUMN is_builtin;
--   DELETE FROM project_styles WHERE id LIKE 'preset-%';

-- 风格目录：结构化分析结果
SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'project_styles'
        AND COLUMN_NAME = 'structured_profile'
    ),
    'SELECT 1',
    'ALTER TABLE project_styles ADD COLUMN structured_profile JSON NULL COMMENT ''AI 分析/人工修订的结构化风格字段'''
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 风格参考图（1–3 张，文件 ID 列表）
SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'project_styles'
        AND COLUMN_NAME = 'reference_file_ids'
    ),
    'SELECT 1',
    'ALTER TABLE project_styles ADD COLUMN reference_file_ids JSON NULL COMMENT ''风格参考图文件 ID 列表（1–3 张）'''
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 已确认样张（人工上传，0–3 张）
SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'project_styles'
        AND COLUMN_NAME = 'sample_file_ids'
    ),
    'SELECT 1',
    'ALTER TABLE project_styles ADD COLUMN sample_file_ids JSON NULL COMMENT ''已确认样张文件 ID 列表'''
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 分析状态：draft / analyzed（失败不改变草稿保存能力）
SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'project_styles'
        AND COLUMN_NAME = 'analysis_status'
    ),
    'SELECT 1',
    'ALTER TABLE project_styles ADD COLUMN analysis_status VARCHAR(16) NOT NULL DEFAULT ''draft'' COMMENT ''AI 分析状态：draft / analyzed'''
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 是否为平台内置模板（首批三个预设）
SET @ddl = (
  SELECT IF(
    EXISTS(
      SELECT 1 FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'project_styles'
        AND COLUMN_NAME = 'is_builtin'
    ),
    'SELECT 1',
    'ALTER TABLE project_styles ADD COLUMN is_builtin TINYINT(1) NOT NULL DEFAULT 0 COMMENT ''是否平台内置模板'''
  )
);
PREPARE stmt FROM @ddl; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- 项目风格名可能是新增模板（不再受旧枚举长度限制）
ALTER TABLE projects MODIFY COLUMN style VARCHAR(64) NOT NULL COMMENT '题材/风格（风格目录名称；兼容历史枚举值）';

-- 项目级风格快照：锁定后与全局目录解耦
CREATE TABLE IF NOT EXISTS project_style_snapshots (
  project_id          VARCHAR(64)  NOT NULL COMMENT '项目 ID',
  source_style_id     VARCHAR(64)  NULL COMMENT '来源风格 ID；目录项删除后置空',
  style_name          VARCHAR(64)  NOT NULL COMMENT '锁定时的风格名称',
  visual_style        VARCHAR(16)  NOT NULL COMMENT '锁定时的画面表现形式',
  description         TEXT         NOT NULL COMMENT '锁定时的风格说明',
  structured_profile  JSON         NULL COMMENT '锁定时的结构化风格字段',
  prompt_pack         TEXT         NOT NULL COMMENT '锁定时的最终提示词质感描述',
  reference_file_ids  JSON         NULL COMMENT '锁定时的风格参考图',
  sample_file_ids     JSON         NULL COMMENT '锁定时的确认样张',
  snapshot_version    INT          NOT NULL DEFAULT 1 COMMENT '快照版本',
  locked_at           DATETIME(6)  NOT NULL COMMENT '锁定时间',
  created_at          DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at          DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (project_id),
  KEY ix_project_style_snapshots_source (source_style_id),
  CONSTRAINT fk_project_style_snapshots_project
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  CONSTRAINT fk_project_style_snapshots_source
    FOREIGN KEY (source_style_id) REFERENCES project_styles(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='项目视觉风格锁定快照';

-- 三个内置模板（稳定 ID；ON DUPLICATE KEY 只更新模板字段，不碰用户自建风格）
INSERT INTO project_styles
  (id, visual_style, name, description, prompt_pack, structured_profile, reference_file_ids, sample_file_ids, analysis_status, is_builtin, sort_order)
VALUES
  (
    'preset-live-action-realism',
    '现实',
    '真人电影写实',
    '电影级实拍质感，真实皮肤与自然光照，适合现实主义都市与剧情短剧。',
    '电影级实拍质感，真实皮肤纹理与自然毛孔，柔和窗光与实用光源混合，浅景深，低饱和电影调色，轻微胶片颗粒',
    JSON_OBJECT(
      'medium', '真人电影实拍',
      'texture', '真实皮肤纹理、自然毛孔与细微瑕疵',
      'color', '低饱和电影调色，肤色自然，暗部保留细节',
      'lighting', '柔和窗光与实用光源混合，体积光克制',
      'material', '棉麻、皮革与金属反射符合物理规律',
      'character_rendering', '真实骨相与面部比例，表情克制，不磨皮',
      'scene_rendering', '实景质感，生活痕迹明确，景深自然',
      'camera', '35–85mm 电影镜头语言，稳定构图，轻微手持感',
      'keep', '真实肤色、自然光比、生活化道具',
      'avoid', '塑料感皮肤、过度磨皮、游戏引擎质感、夸张霓虹'
    ),
    JSON_ARRAY(),
    JSON_ARRAY(),
    'draft',
    1,
    100
  ),
  (
    'preset-2d-animation',
    '动漫',
    '2D 动画',
    '日式二维动画赛璐璐质感，干净线稿与明确色块，适合漫剧与轻喜剧。',
    '日式二维动画赛璐璐上色，干净线稿与清晰描边，色块分区明确，柔和渐变阴影，无真实皮肤纹理',
    JSON_OBJECT(
      'medium', '2D 日式动画',
      'texture', '赛璐璐平涂，干净线稿，轻微纸张质感',
      'color', '明快但不过饱和，主色明确，阴影色偏冷',
      'lighting', '二维光影分层，边缘光简洁，避免复杂全局光',
      'material', '布料与头发以色块和线条表达',
      'character_rendering', '稳定五官比例，清晰发丝分组，表情符号化但不过度夸张',
      'scene_rendering', '背景绘制感明确，透视简洁，细节服务于主体',
      'camera', '动画构图，常用推拉与横移，避免真实镜头畸变',
      'keep', '线稿一致、色块干净、角色五官比例稳定',
      'avoid', '真实皮肤纹理、三维渲染高光、照片质感、厚涂油画'
    ),
    JSON_ARRAY(),
    JSON_ARRAY(),
    'draft',
    1,
    101
  ),
  (
    'preset-3d-chinese-anime',
    '动漫',
    '3D 国漫',
    '三维国漫渲染，柔和全局光照与东方审美，适合仙侠、古风与玄幻题材。',
    '三维国漫渲染，柔和全局光照与次表面散射，东方审美造型，低饱和国风配色，材质层次清晰',
    JSON_OBJECT(
      'medium', '3D 国漫渲染',
      'texture', '柔和次表面散射，布料与皮肤质感细腻',
      'color', '低饱和国风配色，青绿与暖金点缀',
      'lighting', '柔和全局光照，体积光与边缘光克制',
      'material', '丝绸、玉石、木材与金属层次清晰',
      'character_rendering', '东方骨相，圆润造型，发丝成组，表情含蓄',
      'scene_rendering', '山水与建筑层次分明，雾气与景深营造空间',
      'camera', '稳定运镜，常用环绕与缓慢推近，避免手持抖动',
      'keep', '东方造型、柔和光照、材质层次、国风配色',
      'avoid', '欧美卡通比例、塑料高光、低模锯齿、写实照片皮肤'
    ),
    JSON_ARRAY(),
    JSON_ARRAY(),
    'draft',
    1,
    102
  )
ON DUPLICATE KEY UPDATE
  visual_style = VALUES(visual_style),
  name = VALUES(name),
  description = VALUES(description),
  prompt_pack = VALUES(prompt_pack),
  structured_profile = VALUES(structured_profile),
  is_builtin = VALUES(is_builtin),
  sort_order = VALUES(sort_order);
