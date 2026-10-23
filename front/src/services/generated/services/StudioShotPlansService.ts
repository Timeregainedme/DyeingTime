/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiResponse_list_ShotAssetVersionRead__ } from '../models/ApiResponse_list_ShotAssetVersionRead__';
import type { ApiResponse_list_ShotPlanDraftRead__ } from '../models/ApiResponse_list_ShotPlanDraftRead__';
import type { ApiResponse_NoneType_ } from '../models/ApiResponse_NoneType_';
import type { ApiResponse_ShotPlanCandidateRead_ } from '../models/ApiResponse_ShotPlanCandidateRead_';
import type { ApiResponse_ShotPlanConfirmRead_ } from '../models/ApiResponse_ShotPlanConfirmRead_';
import type { ApiResponse_ShotPlanDraftRead_ } from '../models/ApiResponse_ShotPlanDraftRead_';
import type { ApiResponse_ShotPlanStatsRead_ } from '../models/ApiResponse_ShotPlanStatsRead_';
import type { ShotPlanCandidateCreate } from '../models/ShotPlanCandidateCreate';
import type { ShotPlanCandidateUpdate } from '../models/ShotPlanCandidateUpdate';
import type { ShotPlanConfirmRequest } from '../models/ShotPlanConfirmRequest';
import type { ShotPlanMergeRequest } from '../models/ShotPlanMergeRequest';
import type { ShotPlanReorderRequest } from '../models/ShotPlanReorderRequest';
import type { ShotPlanRequest } from '../models/ShotPlanRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class StudioShotPlansService {
    /**
     * 创建 AI 分镜规划任务
     * @returns ApiResponse_ShotPlanDraftRead_ Successful Response
     * @throws ApiError
     */
    public static createShotPlanApiApiV1StudioChaptersChapterIdShotPlansPost({
        chapterId,
        requestBody,
    }: {
        chapterId: string,
        requestBody: ShotPlanRequest,
    }): CancelablePromise<ApiResponse_ShotPlanDraftRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/chapters/{chapter_id}/shot-plans',
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
     * 剧集分镜规划历史
     * @returns ApiResponse_list_ShotPlanDraftRead__ Successful Response
     * @throws ApiError
     */
    public static listShotPlansApiApiV1StudioChaptersChapterIdShotPlansGet({
        chapterId,
    }: {
        chapterId: string,
    }): CancelablePromise<ApiResponse_list_ShotPlanDraftRead__> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/chapters/{chapter_id}/shot-plans',
            path: {
                'chapter_id': chapterId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 剧集分镜规划统计
     * @returns ApiResponse_ShotPlanStatsRead_ Successful Response
     * @throws ApiError
     */
    public static getShotPlanStatsApiApiV1StudioChaptersChapterIdShotPlanStatsGet({
        chapterId,
    }: {
        chapterId: string,
    }): CancelablePromise<ApiResponse_ShotPlanStatsRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/chapters/{chapter_id}/shot-plan-stats',
            path: {
                'chapter_id': chapterId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 分镜规划草稿详情
     * @returns ApiResponse_ShotPlanDraftRead_ Successful Response
     * @throws ApiError
     */
    public static getShotPlanApiApiV1StudioShotPlansDraftIdGet({
        draftId,
    }: {
        draftId: string,
    }): CancelablePromise<ApiResponse_ShotPlanDraftRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/shot-plans/{draft_id}',
            path: {
                'draft_id': draftId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 编辑/接受/忽略分镜候选
     * @returns ApiResponse_ShotPlanCandidateRead_ Successful Response
     * @throws ApiError
     */
    public static updateShotPlanCandidateApiApiV1StudioShotPlansDraftIdCandidatesCandidateIdPatch({
        draftId,
        candidateId,
        requestBody,
    }: {
        draftId: string,
        candidateId: string,
        requestBody: ShotPlanCandidateUpdate,
    }): CancelablePromise<ApiResponse_ShotPlanCandidateRead_> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/studio/shot-plans/{draft_id}/candidates/{candidate_id}',
            path: {
                'draft_id': draftId,
                'candidate_id': candidateId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 删除镜头候选
     * @returns ApiResponse_NoneType_ Successful Response
     * @throws ApiError
     */
    public static deleteShotPlanCandidateApiApiV1StudioShotPlansDraftIdCandidatesCandidateIdDelete({
        draftId,
        candidateId,
    }: {
        draftId: string,
        candidateId: string,
    }): CancelablePromise<ApiResponse_NoneType_> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/studio/shot-plans/{draft_id}/candidates/{candidate_id}',
            path: {
                'draft_id': draftId,
                'candidate_id': candidateId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 人工新增分镜候选
     * @returns ApiResponse_ShotPlanCandidateRead_ Successful Response
     * @throws ApiError
     */
    public static addShotPlanCandidateApiApiV1StudioShotPlansDraftIdCandidatesPost({
        draftId,
        requestBody,
    }: {
        draftId: string,
        requestBody: ShotPlanCandidateCreate,
    }): CancelablePromise<ApiResponse_ShotPlanCandidateRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/shot-plans/{draft_id}/candidates',
            path: {
                'draft_id': draftId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 复制镜头候选（用于拆分）
     * @returns ApiResponse_ShotPlanCandidateRead_ Successful Response
     * @throws ApiError
     */
    public static duplicateShotPlanCandidateApiApiV1StudioShotPlansDraftIdCandidatesCandidateIdDuplicatePost({
        draftId,
        candidateId,
    }: {
        draftId: string,
        candidateId: string,
    }): CancelablePromise<ApiResponse_ShotPlanCandidateRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/shot-plans/{draft_id}/candidates/{candidate_id}/duplicate',
            path: {
                'draft_id': draftId,
                'candidate_id': candidateId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 镜头候选排序
     * @returns ApiResponse_ShotPlanDraftRead_ Successful Response
     * @throws ApiError
     */
    public static reorderShotPlanCandidatesApiApiV1StudioShotPlansDraftIdReorderPost({
        draftId,
        requestBody,
    }: {
        draftId: string,
        requestBody: ShotPlanReorderRequest,
    }): CancelablePromise<ApiResponse_ShotPlanDraftRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/shot-plans/{draft_id}/reorder',
            path: {
                'draft_id': draftId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 合并相邻镜头候选
     * @returns ApiResponse_ShotPlanCandidateRead_ Successful Response
     * @throws ApiError
     */
    public static mergeShotPlanCandidatesApiApiV1StudioShotPlansDraftIdMergePost({
        draftId,
        requestBody,
    }: {
        draftId: string,
        requestBody: ShotPlanMergeRequest,
    }): CancelablePromise<ApiResponse_ShotPlanCandidateRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/shot-plans/{draft_id}/merge',
            path: {
                'draft_id': draftId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 应用确认后的分镜规划
     * @returns ApiResponse_ShotPlanConfirmRead_ Successful Response
     * @throws ApiError
     */
    public static confirmShotPlanApiApiV1StudioShotPlansDraftIdConfirmPost({
        draftId,
        requestBody,
    }: {
        draftId: string,
        requestBody: ShotPlanConfirmRequest,
    }): CancelablePromise<ApiResponse_ShotPlanConfirmRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/shot-plans/{draft_id}/confirm',
            path: {
                'draft_id': draftId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 镜头资产版本选择
     * @returns ApiResponse_list_ShotAssetVersionRead__ Successful Response
     * @throws ApiError
     */
    public static listShotAssetVersionsApiApiV1StudioShotsShotIdAssetVersionsGet({
        shotId,
    }: {
        shotId: string,
    }): CancelablePromise<ApiResponse_list_ShotAssetVersionRead__> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/shots/{shot_id}/asset-versions',
            path: {
                'shot_id': shotId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
