-- 037-add-script-parse-runs.sql
--
-- P3 / C6：AI 解析运行与可审核候选。
--
-- 关键约束：
-- - candidates 按 (run_id, candidate_type, candidate_key) 唯一，重复写候选可幂等；
-- - 审核状态、匹配实体、合并目标、issue 都是独立列，便于过滤与统计；
-- - 复杂业务内容放 payload JSON，但关联/版本/状态保持结构化列。
--
-- 回滚：
--   DROP TABLE IF EXISTS script_parse_candidates;
--   DROP TABLE IF EXISTS script_parse_runs;

CREATE TABLE IF NOT EXISTS script_parse_runs (
  id                       VARCHAR(64)  NOT NULL COMMENT '解析运行 ID',
  document_id              VARCHAR(64)  NOT NULL COMMENT '剧本文档 ID',
  version_id               VARCHAR(64)  NOT NULL COMMENT '剧本版本 ID',
  worldbuilding_version_id VARCHAR(64)  NULL COMMENT '世界观版本 ID',
  task_id                  VARCHAR(64)  NULL COMMENT '异步任务 ID',
  status                   VARCHAR(16)  NOT NULL DEFAULT 'pending' COMMENT 'pending/running/completed/failed/confirmed',
  progress                 INT          NOT NULL DEFAULT 0,
  model_id                 VARCHAR(64)  NULL,
  model_name               VARCHAR(255) NOT NULL DEFAULT '',
  provider_name            VARCHAR(255) NOT NULL DEFAULT '',
  prompt_version           VARCHAR(64)  NOT NULL DEFAULT '',
  prompt_hash              VARCHAR(64)  NOT NULL DEFAULT '',
  input_hash               VARCHAR(64)  NOT NULL DEFAULT '',
  chunk_count              INT          NOT NULL DEFAULT 1,
  failed_chunks            JSON         NULL,
  error                    TEXT         NOT NULL,
  started_at               DATETIME(6)  NULL,
  finished_at              DATETIME(6)  NULL,
  confirmed_at             DATETIME(6)  NULL,
  confirmed_by             INT          NULL,
  applied_summary          JSON         NULL,
  confirmed_result         JSON         NULL,
  created_at               DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at               DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY ix_script_parse_runs_document (document_id),
  KEY ix_script_parse_runs_version (version_id),
  KEY ix_script_parse_runs_world (worldbuilding_version_id),
  KEY ix_script_parse_runs_task (task_id),
  KEY ix_script_parse_runs_input_hash (input_hash),
  CONSTRAINT fk_script_parse_runs_document
    FOREIGN KEY (document_id) REFERENCES script_documents(id) ON DELETE CASCADE,
  CONSTRAINT fk_script_parse_runs_version
    FOREIGN KEY (version_id) REFERENCES script_document_versions(id) ON DELETE CASCADE,
  CONSTRAINT fk_script_parse_runs_world
    FOREIGN KEY (worldbuilding_version_id) REFERENCES script_document_versions(id) ON DELETE SET NULL,
  CONSTRAINT fk_script_parse_runs_task
    FOREIGN KEY (task_id) REFERENCES generation_tasks(id) ON DELETE SET NULL,
  CONSTRAINT fk_script_parse_runs_confirmed_by
    FOREIGN KEY (confirmed_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='AI 剧本解析运行';

CREATE TABLE IF NOT EXISTS script_parse_candidates (
  id                VARCHAR(64)  NOT NULL COMMENT '候选 ID',
  run_id            VARCHAR(64)  NOT NULL COMMENT '解析运行 ID',
  candidate_type    VARCHAR(32)  NOT NULL COMMENT 'character/scene/prop/costume_change/scene_beat/dialogue/issue',
  candidate_key     VARCHAR(160) NOT NULL DEFAULT '' COMMENT '运行内稳定键',
  order_index       INT          NOT NULL DEFAULT 0,
  payload           JSON         NOT NULL,
  evidence          JSON         NOT NULL,
  review_status     VARCHAR(16)  NOT NULL DEFAULT 'pending' COMMENT 'pending/edited/accepted/ignored/merged',
  matched_entity_id VARCHAR(64)  NULL,
  merged_into_id    VARCHAR(64)  NULL,
  issue             VARCHAR(255) NOT NULL DEFAULT '',
  created_at        DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at        DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_script_parse_candidate_key (run_id, candidate_type, candidate_key),
  KEY ix_script_parse_candidates_run_type (run_id, candidate_type),
  KEY ix_script_parse_candidates_entity (matched_entity_id),
  KEY ix_script_parse_candidates_merged (merged_into_id),
  CONSTRAINT fk_script_parse_candidates_run
    FOREIGN KEY (run_id) REFERENCES script_parse_runs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='AI 解析候选（可人工编辑/合并/忽略）';
