/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 关键帧提示词渲染后的图片映射关系。
 */
export type ShotFramePromptMappingRead = {
    /**
     * 提示词中的图片占位 token，如 图1 / 图2
     */
    token: string;
    /**
     * 实体类型：character/prop/scene/costume
     */
    type: 'character' | 'prop' | 'scene' | 'costume';
    /**
     * 实体 ID（如 character_id/prop_id/scene_id/costume_id）
     */
    id: string;
    /**
     * 实体名称
     */
    name: string;
    /**
     * 本次渲染与生成使用的文件 ID
     */
    file_id: string;
};

