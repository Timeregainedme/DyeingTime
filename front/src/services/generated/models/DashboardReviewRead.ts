/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 待审核事项。
 *
 * `kind` 决定前端跳转位置：
 * - shot_extraction → 剧集镜头准备
 * - shot_plan → 分镜规划审核
 * - video_candidate → 视频候选审核
 */
export type DashboardReviewRead = {
    kind: 'shot_extraction' | 'shot_plan' | 'video_candidate';
    label: string;
    count: number;
    project_id?: (string | null);
    project_name?: (string | null);
    chapter_id?: (string | null);
};

