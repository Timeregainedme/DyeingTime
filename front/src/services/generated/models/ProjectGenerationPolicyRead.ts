/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 生成策略的生效值。
 */
export type ProjectGenerationPolicyRead = {
    reference_mode: string;
    video_concurrency: number;
    max_concurrency: number;
    default_shot_duration: number;
    duration_min: number;
    duration_max: number;
    provider_duration_min?: (number | null);
    provider_duration_max?: (number | null);
    use_dialog_audio_as_reference: boolean;
};

