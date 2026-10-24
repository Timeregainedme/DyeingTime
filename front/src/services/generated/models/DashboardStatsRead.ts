/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 顶部四个统计卡片。口径见各字段说明，全部按当前工作区过滤。
 */
export type DashboardStatsRead = {
    /**
     * 当前工作区项目总数
     */
    project_count: number;
    /**
     * 存在已成功生成视频、但该视频任务尚未人工审核的镜头数
     */
    pending_review_shots: number;
    /**
     * 当前工作区处于 pending/running/streaming 的任务数
     */
    running_tasks: number;
    /**
     * 已采纳视频（shots.generated_video_file_id 非空）的镜头数
     */
    adopted_videos: number;
};

