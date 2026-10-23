-- 047-add-character-voice-samples.sql
-- P6：角色固定音色样本（区别于 characters.voice_id 供应商音色 ID）。
-- 回滚：DROP TABLE IF EXISTS character_voice_samples;

CREATE TABLE IF NOT EXISTS character_voice_samples (
  id           INT          NOT NULL AUTO_INCREMENT,
  character_id VARCHAR(64)  NOT NULL,
  file_id      VARCHAR(64)  NULL,
  label        VARCHAR(255) NOT NULL DEFAULT '',
  is_active    TINYINT(1)   NOT NULL DEFAULT 1,
  created_at   DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at   DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  KEY ix_character_voice_samples_char_active (character_id, is_active),
  CONSTRAINT fk_character_voice_samples_character FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
  CONSTRAINT fk_character_voice_samples_file FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='角色固定音色样本';
