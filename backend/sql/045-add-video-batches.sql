-- 045-add-video-batches.sql
--
-- P6 / C13：视频批量生成批次与子任务。
-- 回滚：
--   DROP TABLE IF EXISTS video_generation_batch_items;
--   DROP TABLE IF EXISTS video_generation_batches;

CREATE TABLE IF NOT EXISTS video_generation_batches (
  id                   VARCHAR(64)  NOT NULL,
  project_id           VARCHAR(64)  NOT NULL,
  chapter_id           VARCHAR(64)  NOT NULL,
  scene_group_id       VARCHAR(64)  NULL,
  requested_by         INT          NULL,
  status               VARCHAR(24)  NOT NULL DEFAULT 'queued',
  candidate_count      INT          NOT NULL DEFAULT 1,
  concurrency          INT          NOT NULL DEFAULT 4,
  total_count          INT          NOT NULL DEFAULT 0,
  queued_count         INT          NOT NULL DEFAULT 0,
  running_count        INT          NOT NULL DEFAULT 0,
  succeeded_count      INT          NOT NULL DEFAULT 0,
  failed_count         INT          NOT NULL DEFAULT 0,
  cancelled_count      INT          NOT NULL DEFAULT 0,
  coverage_snapshot    JSON         NOT NULL,
  error                TEXT         NOT NULL,
  started_at           DATETIME(6)  NULL,
  finished_at          DATETIME(6)  NULL,
  coordinator_task_id  VARCHAR(64)  NULL,
  created_at           DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at           DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY ix_video_batches_chapter_status (chapter_id, status),
  KEY ix_video_batches_project (project_id),
  CONSTRAINT fk_video_batches_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  CONSTRAINT fk_video_batches_chapter FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE,
  CONSTRAINT fk_video_batches_scene_group FOREIGN KEY (scene_group_id) REFERENCES scene_groups(id) ON DELETE SET NULL,
  CONSTRAINT fk_video_batches_requested_by FOREIGN KEY (requested_by) REFERENCES users(id) ON DELETE SET NULL,
  CONSTRAINT fk_video_batches_coordinator FOREIGN KEY (coordinator_task_id) REFERENCES generation_tasks(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='视频批量生成批次';

CREATE TABLE IF NOT EXISTS video_generation_batch_items (
  id              INT          NOT NULL AUTO_INCREMENT,
  batch_id        VARCHAR(64)  NOT NULL,
  shot_id         VARCHAR(64)  NOT NULL,
  candidate_index INT          NOT NULL DEFAULT 1,
  task_id         VARCHAR(64)  NULL,
  status          VARCHAR(24)  NOT NULL DEFAULT 'queued',
  error           TEXT         NOT NULL,
  enqueued_at     DATETIME(6)  NULL,
  completed_at    DATETIME(6)  NULL,
  created_at      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_video_batch_shot_candidate (batch_id, shot_id, candidate_index),
  KEY ix_video_batch_items_batch_status (batch_id, status),
  KEY ix_video_batch_items_task (task_id),
  CONSTRAINT fk_video_batch_items_batch FOREIGN KEY (batch_id) REFERENCES video_generation_batches(id) ON DELETE CASCADE,
  CONSTRAINT fk_video_batch_items_shot FOREIGN KEY (shot_id) REFERENCES shots(id) ON DELETE CASCADE,
  CONSTRAINT fk_video_batch_items_task FOREIGN KEY (task_id) REFERENCES generation_tasks(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='视频批量生成子任务';
