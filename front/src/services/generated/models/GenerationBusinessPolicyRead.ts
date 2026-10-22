/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 内部生产业务约束（与供应商能力分开）。
 */
export type GenerationBusinessPolicyRead = {
    duration_min: number;
    duration_max: number;
    default_shot_duration: number;
    default_concurrency: number;
    max_concurrency: number;
    default_reference_mode: string;
    allowed_reference_modes: Array<string>;
    use_dialog_audio_as_reference_default: boolean;
};

