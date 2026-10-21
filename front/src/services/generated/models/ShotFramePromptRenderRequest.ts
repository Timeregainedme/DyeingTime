/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ShotFrameType } from './ShotFrameType';
import type { ShotLinkedAssetItem } from './ShotLinkedAssetItem';
/**
 * 镜头分镜帧提示词渲染请求体。
 */
export type ShotFramePromptRenderRequest = {
    /**
     * first | last | key
     */
    frame_type: ShotFrameType;
    /**
     * 原始基础提示词。渲染接口要求显式传入，用于生成最终提示词。
     */
    prompt: string;
    /**
     * 参考资产条目列表（可多张，顺序有效）。后端会使用 item.file_id 作为参考图；无效条目会被跳过。
     */
    images?: Array<ShotLinkedAssetItem>;
};

