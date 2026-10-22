/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiResponse_NoneType_ } from '../models/ApiResponse_NoneType_';
import type { ApiResponse_PaginatedData_ProjectRead__ } from '../models/ApiResponse_PaginatedData_ProjectRead__';
import type { ApiResponse_ProjectCharacterRecurrenceRead_ } from '../models/ApiResponse_ProjectCharacterRecurrenceRead_';
import type { ApiResponse_ProjectGenerationConfigRead_ } from '../models/ApiResponse_ProjectGenerationConfigRead_';
import type { ApiResponse_ProjectGenerationOptionsRead_ } from '../models/ApiResponse_ProjectGenerationOptionsRead_';
import type { ApiResponse_ProjectProductionReadinessRead_ } from '../models/ApiResponse_ProjectProductionReadinessRead_';
import type { ApiResponse_ProjectRead_ } from '../models/ApiResponse_ProjectRead_';
import type { ApiResponse_ProjectStyleOptionsRead_ } from '../models/ApiResponse_ProjectStyleOptionsRead_';
import type { ApiResponse_ProjectStyleStateRead_ } from '../models/ApiResponse_ProjectStyleStateRead_';
import type { ProjectCreate } from '../models/ProjectCreate';
import type { ProjectGenerationConfigUpdate } from '../models/ProjectGenerationConfigUpdate';
import type { ProjectStyleLockRequest } from '../models/ProjectStyleLockRequest';
import type { ProjectStyleSelectRequest } from '../models/ProjectStyleSelectRequest';
import type { ProjectUpdate } from '../models/ProjectUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class StudioProjectsService {
    /**
     * 获取项目风格候选项
     * @returns ApiResponse_ProjectStyleOptionsRead_ Successful Response
     * @throws ApiError
     */
    public static getProjectStyleOptionsApiV1StudioProjectsStyleOptionsGet(): CancelablePromise<ApiResponse_ProjectStyleOptionsRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/projects/style-options',
        });
    }
    /**
     * 项目可选模型与能力
     * 项目配置面板的模型清单。
     *
     * 只返回模型 ID、名称、供应商与能力，不返回任何 API Key / Base URL。
     * @returns ApiResponse_ProjectGenerationOptionsRead_ Successful Response
     * @throws ApiError
     */
    public static getProjectGenerationOptionsApiApiV1StudioProjectsProjectIdGenerationOptionsGet({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<ApiResponse_ProjectGenerationOptionsRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/projects/{project_id}/generation-options',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 读取项目生成配置
     * @returns ApiResponse_ProjectGenerationConfigRead_ Successful Response
     * @throws ApiError
     */
    public static getProjectGenerationConfigApiApiV1StudioProjectsProjectIdGenerationConfigGet({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<ApiResponse_ProjectGenerationConfigRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/projects/{project_id}/generation-config',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 保存并确认项目生成配置
     * 保存项目配置。
     *
     * `confirm=true` 会在服务端重新执行能力校验并写入快照；
     * 校验失败返回 400，不写入任何字段（事务回滚）。
     * @returns ApiResponse_ProjectGenerationConfigRead_ Successful Response
     * @throws ApiError
     */
    public static saveProjectGenerationConfigApiApiV1StudioProjectsProjectIdGenerationConfigPut({
        projectId,
        requestBody,
    }: {
        projectId: string,
        requestBody: ProjectGenerationConfigUpdate,
    }): CancelablePromise<ApiResponse_ProjectGenerationConfigRead_> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/studio/projects/{project_id}/generation-config',
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
     * 读取项目视觉风格与锁定状态
     * @returns ApiResponse_ProjectStyleStateRead_ Successful Response
     * @throws ApiError
     */
    public static getProjectStyleStateApiApiV1StudioProjectsProjectIdStyleGet({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<ApiResponse_ProjectStyleStateRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/projects/{project_id}/style',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 选择项目视觉风格（未锁定前）
     * @returns ApiResponse_ProjectStyleStateRead_ Successful Response
     * @throws ApiError
     */
    public static selectProjectStyleApiApiV1StudioProjectsProjectIdStylePut({
        projectId,
        requestBody,
    }: {
        projectId: string,
        requestBody: ProjectStyleSelectRequest,
    }): CancelablePromise<ApiResponse_ProjectStyleStateRead_> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/studio/projects/{project_id}/style',
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
     * 锁定项目视觉风格并生成快照
     * @returns ApiResponse_ProjectStyleStateRead_ Successful Response
     * @throws ApiError
     */
    public static lockProjectStyleApiApiV1StudioProjectsProjectIdStyleLockPost({
        projectId,
        requestBody,
    }: {
        projectId: string,
        requestBody: ProjectStyleLockRequest,
    }): CancelablePromise<ApiResponse_ProjectStyleStateRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/projects/{project_id}/style/lock',
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
     * 项目列表（分页）
     * @returns ApiResponse_PaginatedData_ProjectRead__ Successful Response
     * @throws ApiError
     */
    public static listProjectsApiV1StudioProjectsGet({
        q,
        order,
        isDesc = false,
        page = 1,
        pageSize = 10,
    }: {
        /**
         * 关键字，过滤 name/description
         */
        q?: (string | null),
        /**
         * 排序字段
         */
        order?: (string | null),
        /**
         * 是否倒序
         */
        isDesc?: boolean,
        page?: number,
        pageSize?: number,
    }): CancelablePromise<ApiResponse_PaginatedData_ProjectRead__> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/projects',
            query: {
                'q': q,
                'order': order,
                'is_desc': isDesc,
                'page': page,
                'page_size': pageSize,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 创建项目
     * @returns ApiResponse_ProjectRead_ Successful Response
     * @throws ApiError
     */
    public static createProjectApiV1StudioProjectsPost({
        requestBody,
    }: {
        requestBody: ProjectCreate,
    }): CancelablePromise<ApiResponse_ProjectRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/projects',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取项目
     * @returns ApiResponse_ProjectRead_ Successful Response
     * @throws ApiError
     */
    public static getProjectApiV1StudioProjectsProjectIdGet({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<ApiResponse_ProjectRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/projects/{project_id}',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 更新项目
     * @returns ApiResponse_ProjectRead_ Successful Response
     * @throws ApiError
     */
    public static updateProjectApiV1StudioProjectsProjectIdPatch({
        projectId,
        requestBody,
    }: {
        projectId: string,
        requestBody: ProjectUpdate,
    }): CancelablePromise<ApiResponse_ProjectRead_> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/studio/projects/{project_id}',
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
     * 删除项目
     * @returns ApiResponse_NoneType_ Successful Response
     * @throws ApiError
     */
    public static deleteProjectApiV1StudioProjectsProjectIdDelete({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<ApiResponse_NoneType_> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/studio/projects/{project_id}',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 项目开工预检
     * 开工前一次性检查：默认模型与 API Key、比例、每角色音色、分镜参考图、提取确认。
     *
     * 只读聚合，不修改任何状态；返回 `ready=false` 时逐项给出缺失原因。
     * @returns ApiResponse_ProjectProductionReadinessRead_ Successful Response
     * @throws ApiError
     */
    public static getProjectProductionReadinessApiApiV1StudioProjectsProjectIdProductionReadinessGet({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<ApiResponse_ProjectProductionReadinessRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/projects/{project_id}/production-readiness',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 角色跨集出现情况
     * 回答「这个项目里哪些角色是主角级、需要绑定演员」。
     *
     * 为什么单独一个端点而不是塞进角色列表：要不要绑演员取决于角色出现在几集里，
     * 而章节数必须经 `shot_character_links ⋈ shots` 才能算出来。做成一次项目级只读查询，
     * 前端在新建/编辑角色时就能把「仅 1 集，可不绑」与「跨 N 集，建议绑」直接标在卡片上。
     * @returns ApiResponse_ProjectCharacterRecurrenceRead_ Successful Response
     * @throws ApiError
     */
    public static getProjectCharacterRecurrenceApiApiV1StudioProjectsProjectIdCharacterRecurrenceGet({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<ApiResponse_ProjectCharacterRecurrenceRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/projects/{project_id}/character-recurrence',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
