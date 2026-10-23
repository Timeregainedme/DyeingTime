/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ShotPlanRequest = {
    /**
     * 目标总时长（秒）
     */
    target_duration?: number;
    /**
     * 镜头节奏：slow/standard/fast
     */
    pace?: 'slow' | 'standard' | 'fast';
    /**
     * 已有同来源草稿时是否重新规划
     */
    force?: boolean;
};

