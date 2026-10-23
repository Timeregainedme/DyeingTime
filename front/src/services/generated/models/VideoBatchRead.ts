/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { VideoBatchItemRead } from './VideoBatchItemRead';
export type VideoBatchRead = {
    id: string;
    project_id: string;
    chapter_id: string;
    scene_group_id?: (string | null);
    status: string;
    candidate_count: number;
    concurrency: number;
    total_count: number;
    queued_count: number;
    running_count: number;
    succeeded_count: number;
    failed_count: number;
    cancelled_count: number;
    coverage_snapshot?: Record<string, any>;
    error?: string;
    started_at?: (string | null);
    finished_at?: (string | null);
    coordinator_task_id?: (string | null);
    created_at?: (string | null);
    items?: Array<VideoBatchItemRead>;
};

