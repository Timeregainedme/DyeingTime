/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { GenerationBusinessPolicyRead } from './GenerationBusinessPolicyRead';
import type { GenerationModelOptionRead } from './GenerationModelOptionRead';
/**
 * 项目配置面板所需的模型清单、全局默认与业务约束。
 */
export type ProjectGenerationOptionsRead = {
    image_models?: Array<GenerationModelOptionRead>;
    video_models?: Array<GenerationModelOptionRead>;
    audio_models?: Array<GenerationModelOptionRead>;
    global_defaults?: Record<string, (string | null)>;
    business: GenerationBusinessPolicyRead;
};

