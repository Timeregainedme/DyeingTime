-- 将历史 shots.status='generating' 回算为静态状态。
-- 说明：
-- 1. 新逻辑下 shot.status 仅表示“信息提取确认状态”：pending / ready
-- 2. 运行中的生成任务应从 GenerationTask / GenerationTaskLink 动态聚合，不再写入 shots.status
-- 3. dialogue candidates 表在部分环境可能尚未创建，因此这里按“存在才参与回算”处理

SET @has_dialogue_candidates_table = (
    SELECT COUNT(*)
    FROM information_schema.TABLES
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'shot_extracted_dialogue_candidates'
);

SET @normalize_shot_status_sql = IF(
    @has_dialogue_candidates_table > 0,
    "
    UPDATE shots AS s
    LEFT JOIN (
        SELECT
            shot_id,
            COUNT(*) AS total_count,
            SUM(CASE WHEN candidate_status = 'pending' THEN 1 ELSE 0 END) AS pending_count
        FROM shot_extracted_candidates
        GROUP BY shot_id
    ) AS ac
        ON ac.shot_id = s.id
    LEFT JOIN (
        SELECT
            shot_id,
            COUNT(*) AS total_count,
            SUM(CASE WHEN candidate_status = 'pending' THEN 1 ELSE 0 END) AS pending_count
        FROM shot_extracted_dialogue_candidates
        GROUP BY shot_id
    ) AS dc
        ON dc.shot_id = s.id
    SET s.status = CASE
        WHEN s.skip_extraction = 1 THEN 'ready'
        WHEN s.last_extracted_at IS NULL THEN 'pending'
        WHEN COALESCE(ac.total_count, 0) = 0 AND COALESCE(dc.total_count, 0) = 0 THEN 'ready'
        WHEN COALESCE(ac.pending_count, 0) = 0 AND COALESCE(dc.pending_count, 0) = 0 THEN 'ready'
        ELSE 'pending'
    END
    WHERE s.status = 'generating'
    ",
    "
    UPDATE shots AS s
    LEFT JOIN (
        SELECT
            shot_id,
            COUNT(*) AS total_count,
            SUM(CASE WHEN candidate_status = 'pending' THEN 1 ELSE 0 END) AS pending_count
        FROM shot_extracted_candidates
        GROUP BY shot_id
    ) AS ac
        ON ac.shot_id = s.id
    SET s.status = CASE
        WHEN s.skip_extraction = 1 THEN 'ready'
        WHEN s.last_extracted_at IS NULL THEN 'pending'
        WHEN COALESCE(ac.total_count, 0) = 0 THEN 'ready'
        WHEN COALESCE(ac.pending_count, 0) = 0 THEN 'ready'
        ELSE 'pending'
    END
    WHERE s.status = 'generating'
    "
);

PREPARE normalize_shot_status_stmt FROM @normalize_shot_status_sql;
EXECUTE normalize_shot_status_stmt;
DEALLOCATE PREPARE normalize_shot_status_stmt;
