/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 变体分析请求。
 */
export type VariantAnalysisRequest = {
    /**
     * 项目 ID（异步任务关联可选）
     */
    project_id?: (string | null);
    /**
     * 章节 ID（异步任务关联可选）
     */
    chapter_id?: (string | null);
    /**
     * 合并后的实体库（EntityLibrary 的序列化形式；来自 EntityMerger 输出的 merged_library）
     */
    merged_library: Record<string, any>;
    /**
     * 所有镜头提取结果
     */
    all_shot_extractions: Array<Record<string, any>>;
    /**
     * 脚本分镜结果（可选；ScriptDivisionResult 序列化），用于章节/段落分组
     */
    script_division?: (Record<string, any> | null);
};

