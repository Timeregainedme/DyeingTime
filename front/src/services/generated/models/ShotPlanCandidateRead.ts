/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ShotPlanCandidateRead = {
    id: string;
    draft_id: string;
    order_index: number;
    scene_group_id?: (string | null);
    candidate_key?: string;
    payload?: Record<string, any>;
    issues?: Array<Record<string, any>>;
    review_status?: string;
    source_key?: (string | null);
    created_at?: (string | null);
};

