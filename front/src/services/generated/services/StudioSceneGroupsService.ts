/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiResponse_list_SceneGroupRead__ } from '../models/ApiResponse_list_SceneGroupRead__';
import type { ApiResponse_list_ShotRead__ } from '../models/ApiResponse_list_ShotRead__';
import type { ApiResponse_NoneType_ } from '../models/ApiResponse_NoneType_';
import type { ApiResponse_SceneGroupImportRead_ } from '../models/ApiResponse_SceneGroupImportRead_';
import type { ApiResponse_SceneGroupRead_ } from '../models/ApiResponse_SceneGroupRead_';
import type { ApiResponse_SceneGroupSuggestionRead_ } from '../models/ApiResponse_SceneGroupSuggestionRead_';
import type { SceneGroupCreate } from '../models/SceneGroupCreate';
import type { SceneGroupImportRequest } from '../models/SceneGroupImportRequest';
import type { SceneGroupReorderRequest } from '../models/SceneGroupReorderRequest';
import type { SceneGroupUpdate } from '../models/SceneGroupUpdate';
import type { ShotReorderRequest } from '../models/ShotReorderRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class StudioSceneGroupsService {
    /**
     * 剧集场次列表
     * @returns ApiResponse_list_SceneGroupRead__ Successful Response
     * @throws ApiError
     */
    public static listSceneGroupsApiApiV1StudioChaptersChapterIdSceneGroupsGet({
        chapterId,
    }: {
        chapterId: string,
    }): CancelablePromise<ApiResponse_list_SceneGroupRead__> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/chapters/{chapter_id}/scene-groups',
            path: {
                'chapter_id': chapterId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 创建场次
     * @returns ApiResponse_SceneGroupRead_ Successful Response
     * @throws ApiError
     */
    public static createSceneGroupApiApiV1StudioChaptersChapterIdSceneGroupsPost({
        chapterId,
        requestBody,
    }: {
        chapterId: string,
        requestBody: SceneGroupCreate,
    }): CancelablePromise<ApiResponse_SceneGroupRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/chapters/{chapter_id}/scene-groups',
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
     * 场次详情
     * @returns ApiResponse_SceneGroupRead_ Successful Response
     * @throws ApiError
     */
    public static getSceneGroupApiApiV1StudioSceneGroupsGroupIdGet({
        groupId,
    }: {
        groupId: string,
    }): CancelablePromise<ApiResponse_SceneGroupRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/scene-groups/{group_id}',
            path: {
                'group_id': groupId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 修改场次
     * @returns ApiResponse_SceneGroupRead_ Successful Response
     * @throws ApiError
     */
    public static updateSceneGroupApiApiV1StudioSceneGroupsGroupIdPatch({
        groupId,
        requestBody,
    }: {
        groupId: string,
        requestBody: SceneGroupUpdate,
    }): CancelablePromise<ApiResponse_SceneGroupRead_> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/studio/scene-groups/{group_id}',
            path: {
                'group_id': groupId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 删除空场次
     * @returns ApiResponse_NoneType_ Successful Response
     * @throws ApiError
     */
    public static deleteSceneGroupApiApiV1StudioSceneGroupsGroupIdDelete({
        groupId,
    }: {
        groupId: string,
    }): CancelablePromise<ApiResponse_NoneType_> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/studio/scene-groups/{group_id}',
            path: {
                'group_id': groupId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 场次排序
     * @returns ApiResponse_list_SceneGroupRead__ Successful Response
     * @throws ApiError
     */
    public static reorderSceneGroupsApiApiV1StudioChaptersChapterIdSceneGroupsReorderPost({
        chapterId,
        requestBody,
    }: {
        chapterId: string,
        requestBody: SceneGroupReorderRequest,
    }): CancelablePromise<ApiResponse_list_SceneGroupRead__> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/chapters/{chapter_id}/scene-groups/reorder',
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
     * 场次镜头列表
     * @returns ApiResponse_list_ShotRead__ Successful Response
     * @throws ApiError
     */
    public static listSceneGroupShotsApiApiV1StudioSceneGroupsGroupIdShotsGet({
        groupId,
    }: {
        groupId: string,
    }): CancelablePromise<ApiResponse_list_ShotRead__> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/scene-groups/{group_id}/shots',
            path: {
                'group_id': groupId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 章节镜头跨场次排序/移动
     * @returns ApiResponse_list_ShotRead__ Successful Response
     * @throws ApiError
     */
    public static reorderChapterShotsApiApiV1StudioChaptersChapterIdShotsReorderPost({
        chapterId,
        requestBody,
    }: {
        chapterId: string,
        requestBody: ShotReorderRequest,
    }): CancelablePromise<ApiResponse_list_ShotRead__> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/chapters/{chapter_id}/shots/reorder',
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
     * P3 场次建议与场次规划来源
     * @returns ApiResponse_SceneGroupSuggestionRead_ Successful Response
     * @throws ApiError
     */
    public static getSceneGroupSuggestionsApiApiV1StudioChaptersChapterIdSceneGroupSuggestionsGet({
        chapterId,
        parseRunId,
    }: {
        chapterId: string,
        parseRunId?: (string | null),
    }): CancelablePromise<ApiResponse_SceneGroupSuggestionRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/chapters/{chapter_id}/scene-group-suggestions',
            path: {
                'chapter_id': chapterId,
            },
            query: {
                'parse_run_id': parseRunId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 导入 P3 场次建议（幂等）
     * @returns ApiResponse_SceneGroupImportRead_ Successful Response
     * @throws ApiError
     */
    public static importSceneGroupSuggestionsApiApiV1StudioChaptersChapterIdSceneGroupsImportPost({
        chapterId,
        requestBody,
    }: {
        chapterId: string,
        requestBody: SceneGroupImportRequest,
    }): CancelablePromise<ApiResponse_SceneGroupImportRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/chapters/{chapter_id}/scene-groups/import',
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
}
