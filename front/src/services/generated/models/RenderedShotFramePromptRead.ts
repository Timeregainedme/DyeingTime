/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { FrameGuidanceDecisionRead } from './FrameGuidanceDecisionRead';
import type { ShotFramePromptMappingRead } from './ShotFramePromptMappingRead';
/**
 * 关键帧最终生成提示词渲染结果。
 */
export type RenderedShotFramePromptRead = {
    /**
     * 原始基础提示词（不含图片映射说明）
     */
    base_prompt: string;
    /**
     * 最终提交给模型的提示词（含图片映射说明）
     */
    rendered_prompt: string;
    /**
     * 最终 prompt 实际保留的 guidance 列表
     */
    selected_guidance?: Array<string>;
    /**
     * 本次渲染中被压缩掉的 guidance 列表
     */
    dropped_guidance?: Array<string>;
    /**
     * 最终保留 guidance 的决策详情
     */
    selected_guidance_details?: Array<FrameGuidanceDecisionRead>;
    /**
     * 被压缩 guidance 的决策详情
     */
    dropped_guidance_details?: Array<FrameGuidanceDecisionRead>;
    /**
     * 最终参考图 file_id 列表，顺序与 mappings 一致
     */
    images?: Array<string>;
    /**
     * 图片与实体名称的映射关系，顺序与 images 完全一致
     */
    mappings?: Array<ShotFramePromptMappingRead>;
};

