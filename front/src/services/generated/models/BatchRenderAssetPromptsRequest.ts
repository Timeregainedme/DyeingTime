/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 批量渲染资产图提示词请求体（不创建图片任务）。
 */
export type BatchRenderAssetPromptsRequest = {
    /**
     * 目标项目 ID
     */
    project_id: string;
    /**
     * 目标资产 ID 列表；缺省为该类型在当前项目下的全部资产
     */
    asset_ids?: (Array<string> | null);
    /**
     * 只渲染还没有审核稿的资产；为 true 时已有审核稿会进入 skipped
     */
    only_missing?: boolean;
};

