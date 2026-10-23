/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiResponse_ClipsExportPrecheckRead_ } from '../models/ApiResponse_ClipsExportPrecheckRead_';
import type { ApiResponse_ProjectTimelineRead_ } from '../models/ApiResponse_ProjectTimelineRead_';
import type { ApiResponse_TimelineExportRead_ } from '../models/ApiResponse_TimelineExportRead_';
import type { ClipsExportRequest } from '../models/ClipsExportRequest';
import type { ClipsExportSelection } from '../models/ClipsExportSelection';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class StudioTimelineService {
    /**
     * 项目时间线（按章节顺序聚合的分镜片段）
     * @returns ApiResponse_ProjectTimelineRead_ Successful Response
     * @throws ApiError
     */
    public static getProjectTimelineApiApiV1StudioTimelineProjectsProjectIdGet({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<ApiResponse_ProjectTimelineRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/timeline/projects/{project_id}',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 导出成片（ffmpeg 拼接全部镜头视频）
     * @returns ApiResponse_TimelineExportRead_ Successful Response
     * @throws ApiError
     */
    public static exportProjectTimelineApiApiV1StudioTimelineProjectsProjectIdExportPost({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<ApiResponse_TimelineExportRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/timeline/projects/{project_id}/export',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 打包导出全部片段视频（zip）
     * 把每个片段的视频原样打包下载。
     *
     * 与「导出成片」互补：成片要求所有片段都有视频并串成一个 mp4；
     * 这里允许部分片段缺失，缺的会写进 zip 里的 MANIFEST 说明文件。
     * @returns any Successful Response
     * @throws ApiError
     */
    public static exportProjectClipsArchiveApiApiV1StudioTimelineProjectsProjectIdClipsArchiveGet({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/timeline/projects/{project_id}/clips-archive',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 选择式 MP4 ZIP 导出预检查
     * 返回镜头顺序、规范化文件名、已采纳文件及所有阻塞项。
     * @returns ApiResponse_ClipsExportPrecheckRead_ Successful Response
     * @throws ApiError
     */
    public static precheckProjectClipsExportApiApiV1StudioTimelineProjectsProjectIdClipsPrecheckPost({
        projectId,
        requestBody,
    }: {
        projectId: string,
        requestBody: ClipsExportSelection,
    }): CancelablePromise<ApiResponse_ClipsExportPrecheckRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/timeline/projects/{project_id}/clips-precheck',
            path: {
                'project_id': projectId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 选择式 MP4 ZIP 导出下载
     * 严格按预检查计划生成 MP4-only ZIP。
     *
     * 该接口不修改任何镜头状态、不触发媒体生成、不删除旧视频。
     * @returns any Successful Response
     * @throws ApiError
     */
    public static exportSelectedClipsApiApiV1StudioTimelineProjectsProjectIdClipsExportPost({
        projectId,
        requestBody,
    }: {
        projectId: string,
        requestBody: ClipsExportRequest,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/timeline/projects/{project_id}/clips-export',
            path: {
                'project_id': projectId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
