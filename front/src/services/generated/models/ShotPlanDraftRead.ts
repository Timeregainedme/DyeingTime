/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ShotPlanCandidateRead } from './ShotPlanCandidateRead';
export type ShotPlanDraftRead = {
    id: string;
    project_id: string;
    chapter_id: string;
    source_parse_run_id?: (string | null);
    source_script_version_id?: (string | null);
    target_duration?: number;
    pace?: string;
    status?: string;
    model_id?: (string | null);
    model_name?: string;
    provider_name?: string;
    prompt_version?: string;
    prompt_hash?: string;
    task_id?: (string | null);
    error?: string;
    scene_group_snapshot?: Array<Record<string, any>>;
    coverage?: Record<string, any>;
    applied_at?: (string | null);
    applied_by?: (number | null);
    created_at?: (string | null);
    updated_at?: (string | null);
    candidates?: Array<ShotPlanCandidateRead>;
};

