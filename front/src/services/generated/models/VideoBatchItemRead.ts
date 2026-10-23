/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type VideoBatchItemRead = {
    id: number;
    batch_id: string;
    shot_id: string;
    candidate_index: number;
    task_id?: (string | null);
    status: string;
    error?: string;
    enqueued_at?: (string | null);
    completed_at?: (string | null);
};

