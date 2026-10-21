/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 实体合并请求。
 */
export type EntityMergerRequest = {
    /**
     * 项目 ID（异步任务关联可选）
     */
    project_id?: (string | null);
    /**
     * 章节 ID（异步任务关联可选）
     */
    chapter_id?: (string | null);
    /**
     * 所有镜头提取结果（ShotElementExtractionResult 的序列化形式）
     */
    all_shot_extractions: Array<Record<string, any>>;
    /**
     * 历史实体库（可选，用于增量合并）
     */
    historical_library?: (Record<string, any> | null);
    /**
     * 脚本分镜结果（可选；ScriptDivisionResult 序列化），用于定位与统计
     */
    script_division?: (Record<string, any> | null);
    /**
     * 上一次合并结果（可选；EntityMergeResult 序列化），用于冲突重试合并
     */
    previous_merge?: (Record<string, any> | null);
    /**
     * 冲突解决建议列表（可选；用于冲突重试合并）
     */
    conflict_resolutions?: null;
};

