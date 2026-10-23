/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type GenerationSnapshotRead = {
    id: string;
    shot_id: string;
    project_id: string;
    chapter_id: string;
    scene_group_id?: (string | null);
    task_id?: (string | null);
    model_id?: (string | null);
    model_name?: string;
    provider_name?: string;
    reference_mode: string;
    manifest?: Array<Record<string, any>>;
    prompt: string;
    natural_prompt?: string;
    advanced_prompt?: string;
    prompt_refs?: Array<Record<string, any>>;
    audio_refs?: Array<Record<string, any>>;
    asset_versions?: Array<Record<string, any>>;
    generation_params?: Record<string, any>;
    style_snapshot?: Record<string, any>;
    duration?: number;
    ratio?: string;
    resolution?: (string | null);
    input_hash?: string;
    created_at?: (string | null);
};

