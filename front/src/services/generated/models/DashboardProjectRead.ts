/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DashboardChapterRead } from './DashboardChapterRead';
/**
 * 项目卡片 + 「继续创作」所需的项目级快照。
 */
export type DashboardProjectRead = {
    id: string;
    name: string;
    description: string;
    style: string;
    visual_style: string;
    updated_at?: (string | null);
    chapter_count: number;
    chapters?: Array<DashboardChapterRead>;
    total_shots: number;
    pending_shots: number;
    ready_shots: number;
    pending_review_shots: number;
    adopted_videos: number;
    running_tasks: number;
};

