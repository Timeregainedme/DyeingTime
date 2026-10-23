/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiResponse_GenerationPreviewRead_ } from '../models/ApiResponse_GenerationPreviewRead_';
import type { ApiResponse_GenerationSnapshotRead_ } from '../models/ApiResponse_GenerationSnapshotRead_';
import type { ApiResponse_list_GenerationSnapshotRead__ } from '../models/ApiResponse_list_GenerationSnapshotRead__';
import type { ApiResponse_list_ReferenceBindingRead__ } from '../models/ApiResponse_list_ReferenceBindingRead__';
import type { ApiResponse_NoneType_ } from '../models/ApiResponse_NoneType_';
import type { ApiResponse_P6VideoTaskCreated_ } from '../models/ApiResponse_P6VideoTaskCreated_';
import type { ApiResponse_PromptResolveRead_ } from '../models/ApiResponse_PromptResolveRead_';
import type { ApiResponse_ReferenceBindingRead_ } from '../models/ApiResponse_ReferenceBindingRead_';
import type { ApiResponse_ShotVideoReadinessRead_ } from '../models/ApiResponse_ShotVideoReadinessRead_';
import type { Body_upload_reference_binding_api_api_v1_studio_shots__shot_id__reference_bindings_upload_post } from '../models/Body_upload_reference_binding_api_api_v1_studio_shots__shot_id__reference_bindings_upload_post';
import type { P6VideoGenerateRequest } from '../models/P6VideoGenerateRequest';
import type { PromptResolveRequest } from '../models/PromptResolveRequest';
import type { ReferenceBindingReorder } from '../models/ReferenceBindingReorder';
import type { ReferenceBindingUpdate } from '../models/ReferenceBindingUpdate';
import type { ShotPromptUpdate } from '../models/ShotPromptUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class StudioShotReferencesService {
    /**
     * P6 H3 多参考生成准备度
     * @returns ApiResponse_ShotVideoReadinessRead_ Successful Response
     * @throws ApiError
     */
    public static getP6ReadinessApiApiV1StudioShotsShotIdP6ReadinessGet({
        shotId,
    }: {
        shotId: string,
    }): CancelablePromise<ApiResponse_ShotVideoReadinessRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/shots/{shot_id}/p6-readiness',
            path: {
                'shot_id': shotId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 镜头参考绑定列表
     * @returns ApiResponse_list_ReferenceBindingRead__ Successful Response
     * @throws ApiError
     */
    public static listReferenceBindingsApiApiV1StudioShotsShotIdReferenceBindingsGet({
        shotId,
        activeOnly = false,
    }: {
        shotId: string,
        activeOnly?: boolean,
    }): CancelablePromise<ApiResponse_list_ReferenceBindingRead__> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/shots/{shot_id}/reference-bindings',
            path: {
                'shot_id': shotId,
            },
            query: {
                'active_only': activeOnly,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 按 P5 资产版本自动推荐参考图
     * @returns ApiResponse_list_ReferenceBindingRead__ Successful Response
     * @throws ApiError
     */
    public static recommendReferenceBindingsApiApiV1StudioShotsShotIdReferenceBindingsRecommendPost({
        shotId,
    }: {
        shotId: string,
    }): CancelablePromise<ApiResponse_list_ReferenceBindingRead__> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/shots/{shot_id}/reference-bindings/recommend',
            path: {
                'shot_id': shotId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 修改参考图锁定/启停/用途
     * @returns ApiResponse_ReferenceBindingRead_ Successful Response
     * @throws ApiError
     */
    public static updateReferenceBindingApiApiV1StudioShotsShotIdReferenceBindingsBindingIdPatch({
        shotId,
        bindingId,
        requestBody,
    }: {
        shotId: string,
        bindingId: number,
        requestBody: ReferenceBindingUpdate,
    }): CancelablePromise<ApiResponse_ReferenceBindingRead_> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/studio/shots/{shot_id}/reference-bindings/{binding_id}',
            path: {
                'shot_id': shotId,
                'binding_id': bindingId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 禁用参考图
     * @returns ApiResponse_NoneType_ Successful Response
     * @throws ApiError
     */
    public static removeReferenceBindingApiApiV1StudioShotsShotIdReferenceBindingsBindingIdDelete({
        shotId,
        bindingId,
    }: {
        shotId: string,
        bindingId: number,
    }): CancelablePromise<ApiResponse_NoneType_> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/studio/shots/{shot_id}/reference-bindings/{binding_id}',
            path: {
                'shot_id': shotId,
                'binding_id': bindingId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 参考图排序
     * @returns ApiResponse_list_ReferenceBindingRead__ Successful Response
     * @throws ApiError
     */
    public static reorderReferenceBindingsApiApiV1StudioShotsShotIdReferenceBindingsReorderPost({
        shotId,
        requestBody,
    }: {
        shotId: string,
        requestBody: ReferenceBindingReorder,
    }): CancelablePromise<ApiResponse_list_ReferenceBindingRead__> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/shots/{shot_id}/reference-bindings/reorder',
            path: {
                'shot_id': shotId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 上传镜头专属参考图
     * @returns ApiResponse_ReferenceBindingRead_ Successful Response
     * @throws ApiError
     */
    public static uploadReferenceBindingApiApiV1StudioShotsShotIdReferenceBindingsUploadPost({
        shotId,
        formData,
        referenceRole = 'shot_composition',
    }: {
        shotId: string,
        formData: Body_upload_reference_binding_api_api_v1_studio_shots__shot_id__reference_bindings_upload_post,
        referenceRole?: string,
    }): CancelablePromise<ApiResponse_ReferenceBindingRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/shots/{shot_id}/reference-bindings/upload',
            path: {
                'shot_id': shotId,
            },
            query: {
                'reference_role': referenceRole,
            },
            formData: formData,
            mediaType: 'multipart/form-data',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 解析 @ 资产引用
     * @returns ApiResponse_PromptResolveRead_ Successful Response
     * @throws ApiError
     */
    public static resolvePromptApiApiV1StudioShotsShotIdPromptResolvePost({
        shotId,
        requestBody,
    }: {
        shotId: string,
        requestBody: PromptResolveRequest,
    }): CancelablePromise<ApiResponse_PromptResolveRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/shots/{shot_id}/prompt/resolve',
            path: {
                'shot_id': shotId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 保存自然语言提示词与 @ 引用
     * @returns ApiResponse_PromptResolveRead_ Successful Response
     * @throws ApiError
     */
    public static savePromptApiApiV1StudioShotsShotIdPromptPut({
        shotId,
        requestBody,
    }: {
        shotId: string,
        requestBody: ShotPromptUpdate,
    }): CancelablePromise<ApiResponse_PromptResolveRead_> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/studio/shots/{shot_id}/prompt',
            path: {
                'shot_id': shotId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 预览 P6 H3 参考清单与最终提示词
     * @returns ApiResponse_GenerationPreviewRead_ Successful Response
     * @throws ApiError
     */
    public static generationPreviewApiApiV1StudioShotsShotIdGenerationPreviewPost({
        shotId,
        requestBody,
    }: {
        shotId: string,
        requestBody: P6VideoGenerateRequest,
    }): CancelablePromise<ApiResponse_GenerationPreviewRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/shots/{shot_id}/generation-preview',
            path: {
                'shot_id': shotId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 创建 P6 单镜头视频任务（显式采纳）
     * @returns ApiResponse_P6VideoTaskCreated_ Successful Response
     * @throws ApiError
     */
    public static createP6VideoTaskApiApiV1StudioShotsShotIdGenerationPost({
        shotId,
        requestBody,
    }: {
        shotId: string,
        requestBody: P6VideoGenerateRequest,
    }): CancelablePromise<ApiResponse_P6VideoTaskCreated_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/shots/{shot_id}/generation',
            path: {
                'shot_id': shotId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 镜头生成输入快照历史
     * @returns ApiResponse_list_GenerationSnapshotRead__ Successful Response
     * @throws ApiError
     */
    public static listGenerationSnapshotsApiApiV1StudioShotsShotIdGenerationSnapshotsGet({
        shotId,
    }: {
        shotId: string,
    }): CancelablePromise<ApiResponse_list_GenerationSnapshotRead__> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/shots/{shot_id}/generation-snapshots',
            path: {
                'shot_id': shotId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 生成输入快照详情
     * @returns ApiResponse_GenerationSnapshotRead_ Successful Response
     * @throws ApiError
     */
    public static getGenerationSnapshotApiApiV1StudioGenerationSnapshotsSnapshotIdGet({
        snapshotId,
    }: {
        snapshotId: string,
    }): CancelablePromise<ApiResponse_GenerationSnapshotRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/generation-snapshots/{snapshot_id}',
            path: {
                'snapshot_id': snapshotId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
