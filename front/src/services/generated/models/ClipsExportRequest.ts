/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 正式导出请求；expected_plan_hash 用于防止预检查后采纳版本变化。
 */
export type ClipsExportRequest = {
    /**
     * 自定义镜头 ID 列表；按数据库业务顺序重排，不按传入顺序
     */
    shot_ids?: (Array<string> | null);
    /**
     * 剧集 ID 列表
     */
    chapter_ids?: (Array<string> | null);
    /**
     * 场次 ID 列表
     */
    scene_group_ids?: (Array<string> | null);
    /**
     * 选择项目内全部镜头
     */
    include_all?: boolean;
    /**
     * 预检查返回的 plan_hash；不一致时拒绝导出
     */
    expected_plan_hash?: (string | null);
};

