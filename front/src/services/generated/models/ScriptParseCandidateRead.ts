/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ScriptParseCandidateRead = {
    id: string;
    run_id: string;
    candidate_type: string;
    candidate_key: string;
    order_index?: number;
    payload?: Record<string, any>;
    evidence?: Array<Record<string, any>>;
    review_status?: string;
    matched_entity_id?: (string | null);
    merged_into_id?: (string | null);
    issue?: string;
    created_at?: (string | null);
};

