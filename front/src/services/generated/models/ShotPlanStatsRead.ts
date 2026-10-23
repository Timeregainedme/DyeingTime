/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ShotPlanStatsRead = {
    chapter_id: string;
    latest_draft_id?: (string | null);
    status?: (string | null);
    target_duration?: (number | null);
    shot_count?: number;
    total_duration?: number;
    min_duration?: (number | null);
    max_duration?: (number | null);
    coverage_ratio?: number;
    blocking_issue_count?: number;
    warning_count?: number;
};

