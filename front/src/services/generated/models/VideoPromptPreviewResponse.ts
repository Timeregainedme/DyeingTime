/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ShotVideoPromptPackRead } from './ShotVideoPromptPackRead';
export type VideoPromptPreviewResponse = {
    /**
     * 最终用于视频生成的提示词
     */
    prompt: string;
    /**
     * 关联参考图 file_id 列表
     */
    images?: Array<string>;
    /**
     * 视频提示词预览上下文包
     */
    pack?: (ShotVideoPromptPackRead | null);
};

