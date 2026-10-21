/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ShotVideoPromptPackRead } from './ShotVideoPromptPackRead';
/**
 * 视频提示词预览结果。
 */
export type ShotVideoPromptPreviewRead = {
    /**
     * 镜头 ID
     */
    shot_id: string;
    /**
     * 使用的提示词模板 ID
     */
    template_id?: (string | null);
    /**
     * 使用的提示词模板名称
     */
    template_name?: (string | null);
    /**
     * 渲染后的提示词
     */
    rendered_prompt: string;
    /**
     * 渲染上下文包
     */
    pack: ShotVideoPromptPackRead;
    /**
     * 渲染时发现的非阻塞提示
     */
    warnings?: Array<string>;
};

