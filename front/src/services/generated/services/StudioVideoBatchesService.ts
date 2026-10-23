/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiResponse_VideoBatchListRead_ } from '../models/ApiResponse_VideoBatchListRead_';
import type { ApiResponse_VideoBatchRead_ } from '../models/ApiResponse_VideoBatchRead_';
import type { VideoBatchCreate } from '../models/VideoBatchCreate';
import type { VideoBatchRetryRequest } from '../models/VideoBatchRetryRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class StudioVideoBatchesService {
    /**
     * 创建视频批量生成批次
     * @returns ApiResponse_VideoBatchRead_ Successful Response
     * @throws ApiError
     */
    public static createVideoBatchApiApiV1StudioChaptersChapterIdVideoBatchesPost({
        chapterId,
        requestBody,
    }: {
        chapterId: string,
        requestBody: VideoBatchCreate,
    }): CancelablePromise<ApiResponse_VideoBatchRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/chapters/{chapter_id}/video-batches',
            path: {
                'chapter_id': chapterId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 剧集视频批次列表
     * @returns ApiResponse_VideoBatchListRead_ Successful Response
     * @throws ApiError
     */
    public static listVideoBatchesApiApiV1StudioChaptersChapterIdVideoBatchesGet({
        chapterId,
    }: {
        chapterId: string,
    }): CancelablePromise<ApiResponse_VideoBatchListRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/chapters/{chapter_id}/video-batches',
            path: {
                'chapter_id': chapterId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 批次状态与子任务
     * @returns ApiResponse_VideoBatchRead_ Successful Response
     * @throws ApiError
     */
    public static getVideoBatchApiApiV1StudioVideoBatchesBatchIdGet({
        batchId,
    }: {
        batchId: string,
    }): CancelablePromise<ApiResponse_VideoBatchRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/video-batches/{batch_id}',
            path: {
                'batch_id': batchId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 取消批次（请求取消正在运行的子任务）
     * @returns ApiResponse_VideoBatchRead_ Successful Response
     * @throws ApiError
     */
    public static cancelVideoBatchApiApiV1StudioVideoBatchesBatchIdCancelPost({
        batchId,
    }: {
        batchId: string,
    }): CancelablePromise<ApiResponse_VideoBatchRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/video-batches/{batch_id}/cancel',
            path: {
                'batch_id': batchId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 重试失败子任务
     * @returns ApiResponse_VideoBatchRead_ Successful Response
     * @throws ApiError
     */
    public static retryVideoBatchApiApiV1StudioVideoBatchesBatchIdRetryPost({
        batchId,
        requestBody,
    }: {
        batchId: string,
        requestBody: VideoBatchRetryRequest,
    }): CancelablePromise<ApiResponse_VideoBatchRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/video-batches/{batch_id}/retry',
            path: {
                'batch_id': batchId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 恢复批次协调器（Worker/API 重启后）
     * @returns ApiResponse_VideoBatchRead_ Successful Response
     * @throws ApiError
     */
    public static resumeVideoBatchApiApiV1StudioVideoBatchesBatchIdResumePost({
        batchId,
    }: {
        batchId: string,
    }): CancelablePromise<ApiResponse_VideoBatchRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/video-batches/{batch_id}/resume',
            path: {
                'batch_id': batchId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
