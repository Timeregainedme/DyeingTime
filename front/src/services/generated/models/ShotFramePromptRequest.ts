/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 镜头分镜帧提示词生成任务请求。
 */
export type ShotFramePromptRequest = {
    /**
     * 镜头 ID
     */
    shot_id: string;
    /**
     * first | last | key
     */
    frame_type: string;
};

