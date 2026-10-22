/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type AssetImageCandidateRead = {
    id: number;
    project_id: string;
    asset_type: string;
    asset_id: string;
    asset_version_id?: (string | null);
    candidate_batch_id: string;
    view_angle: string;
    quality_level: string;
    file_id?: (string | null);
    file_url?: string;
    source?: string;
    generation_task_id?: (string | null);
    prompt?: string;
    generation_params?: Record<string, any>;
    status?: string;
    width?: (number | null);
    height?: (number | null);
    format?: string;
    is_adopted?: boolean;
    adopted_at?: (string | null);
    adopted_by?: (number | null);
    created_at?: (string | null);
};

