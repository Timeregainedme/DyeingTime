/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PromptReferenceRead } from './PromptReferenceRead';
import type { ReferenceBindingRead } from './ReferenceBindingRead';
export type GenerationPreviewRead = {
    shot_id: string;
    reference_mode?: string;
    manifest?: Array<ReferenceBindingRead>;
    images?: Array<string>;
    audio_file_ids?: Array<string>;
    prompt?: string;
    natural_prompt?: string;
    advanced_prompt?: string;
    prompt_refs?: Array<PromptReferenceRead>;
    warnings?: Array<string>;
    blocking_errors?: Array<string>;
    model_name?: string;
    provider_name?: string;
    ratio?: string;
    resolution?: (string | null);
    duration?: number;
    input_hash?: string;
    ir?: Record<string, any>;
};

