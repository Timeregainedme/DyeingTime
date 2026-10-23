-- 046-add-shot-video-reviews.sql
-- P6 / C14：视频候选人工审核（标签、备注、满意/不满意）。采纳仍由 shots.generated_video_file_id 表达。
-- 回滚：DROP TABLE IF EXISTS shot_video_reviews;

CREATE TABLE IF NOT EXISTS shot_video_reviews (
  id            INT          NOT NULL AUTO_INCREMENT,
  shot_id       VARCHAR(64)  NOT NULL,
  task_id       VARCHAR(64)  NOT NULL,
  file_id       VARCHAR(64)  NULL,
  review_status VARCHAR(16)  NOT NULL DEFAULT 'unrated',
  issue_tags    JSON         NOT NULL,
  note          TEXT         NOT NULL,
  reviewed_by   INT          NULL,
  reviewed_at   DATETIME(6)  NULL,
  created_at    DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at    DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_shot_video_reviews_task (task_id),
  KEY ix_shot_video_reviews_shot_status (shot_id, review_status),
  CONSTRAINT fk_shot_video_reviews_shot FOREIGN KEY (shot_id) REFERENCES shots(id) ON DELETE CASCADE,
  CONSTRAINT fk_shot_video_reviews_task FOREIGN KEY (task_id) REFERENCES generation_tasks(id) ON DELETE CASCADE,
  CONSTRAINT fk_shot_video_reviews_file FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE SET NULL,
  CONSTRAINT fk_shot_video_reviews_reviewed_by FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='镜头视频候选人工审核';
