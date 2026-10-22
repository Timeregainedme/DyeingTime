/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiResponse_AssetProfileRead_ } from '../models/ApiResponse_AssetProfileRead_';
import type { ApiResponse_CharacterAliasRead_ } from '../models/ApiResponse_CharacterAliasRead_';
import type { ApiResponse_list_AssetImageCandidateRead__ } from '../models/ApiResponse_list_AssetImageCandidateRead__';
import type { ApiResponse_list_AssetVersionRead__ } from '../models/ApiResponse_list_AssetVersionRead__';
import type { ApiResponse_NoneType_ } from '../models/ApiResponse_NoneType_';
import type { ApiResponse_VoiceBindingRead_ } from '../models/ApiResponse_VoiceBindingRead_';
import type { AssetProfileUpdate } from '../models/AssetProfileUpdate';
import type { Body_upload_asset_candidate_api_api_v1_studio_projects__project_id__assets__asset_type___asset_id__candidates_upload_post } from '../models/Body_upload_asset_candidate_api_api_v1_studio_projects__project_id__assets__asset_type___asset_id__candidates_upload_post';
import type { CandidateAdoptRequest } from '../models/CandidateAdoptRequest';
import type { CharacterAliasCreate } from '../models/CharacterAliasCreate';
import type { CharacterAliasUpdate } from '../models/CharacterAliasUpdate';
import type { CharacterLockRequest } from '../models/CharacterLockRequest';
import type { CreateDerivedVersionRequest } from '../models/CreateDerivedVersionRequest';
import type { GenerateCandidatesRequest } from '../models/GenerateCandidatesRequest';
import type { SwitchVersionRequest } from '../models/SwitchVersionRequest';
import type { VoiceBindingUpdate } from '../models/VoiceBindingUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class StudioAssetProfilesService {
    /**
     * 资产档案（角色圣经/资产版本/候选图/音色）
     * @returns ApiResponse_AssetProfileRead_ Successful Response
     * @throws ApiError
     */
    public static getAssetProfileApiApiV1StudioProjectsProjectIdAssetsAssetTypeAssetIdProfileGet({
        projectId,
        assetType,
        assetId,
    }: {
        projectId: string,
        assetType: string,
        assetId: string,
    }): CancelablePromise<ApiResponse_AssetProfileRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/projects/{project_id}/assets/{asset_type}/{asset_id}/profile',
            path: {
                'project_id': projectId,
                'asset_type': assetType,
                'asset_id': assetId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 更新资产文字档案
     * @returns ApiResponse_AssetProfileRead_ Successful Response
     * @throws ApiError
     */
    public static updateAssetProfileApiApiV1StudioProjectsProjectIdAssetsAssetTypeAssetIdProfilePatch({
        projectId,
        assetType,
        assetId,
        requestBody,
    }: {
        projectId: string,
        assetType: string,
        assetId: string,
        requestBody: AssetProfileUpdate,
    }): CancelablePromise<ApiResponse_AssetProfileRead_> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/studio/projects/{project_id}/assets/{asset_type}/{asset_id}/profile',
            path: {
                'project_id': projectId,
                'asset_type': assetType,
                'asset_id': assetId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 新增角色别名
     * @returns ApiResponse_CharacterAliasRead_ Successful Response
     * @throws ApiError
     */
    public static addCharacterAliasApiApiV1StudioProjectsProjectIdAssetsCharacterAssetIdAliasesPost({
        projectId,
        assetId,
        requestBody,
    }: {
        projectId: string,
        assetId: string,
        requestBody: CharacterAliasCreate,
    }): CancelablePromise<ApiResponse_CharacterAliasRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/projects/{project_id}/assets/character/{asset_id}/aliases',
            path: {
                'project_id': projectId,
                'asset_id': assetId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 修改角色别名
     * @returns ApiResponse_CharacterAliasRead_ Successful Response
     * @throws ApiError
     */
    public static updateCharacterAliasApiApiV1StudioProjectsProjectIdAssetsCharacterAssetIdAliasesAliasIdPatch({
        projectId,
        assetId,
        aliasId,
        requestBody,
    }: {
        projectId: string,
        assetId: string,
        aliasId: number,
        requestBody: CharacterAliasUpdate,
    }): CancelablePromise<ApiResponse_CharacterAliasRead_> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/studio/projects/{project_id}/assets/character/{asset_id}/aliases/{alias_id}',
            path: {
                'project_id': projectId,
                'asset_id': assetId,
                'alias_id': aliasId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 删除角色别名
     * @returns ApiResponse_NoneType_ Successful Response
     * @throws ApiError
     */
    public static deleteCharacterAliasApiApiV1StudioProjectsProjectIdAssetsCharacterAssetIdAliasesAliasIdDelete({
        projectId,
        assetId,
        aliasId,
    }: {
        projectId: string,
        assetId: string,
        aliasId: number,
    }): CancelablePromise<ApiResponse_NoneType_> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/studio/projects/{project_id}/assets/character/{asset_id}/aliases/{alias_id}',
            path: {
                'project_id': projectId,
                'asset_id': assetId,
                'alias_id': aliasId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 资产版本历史
     * @returns ApiResponse_list_AssetVersionRead__ Successful Response
     * @throws ApiError
     */
    public static listAssetVersionsApiApiV1StudioProjectsProjectIdAssetsAssetTypeAssetIdVersionsGet({
        projectId,
        assetType,
        assetId,
    }: {
        projectId: string,
        assetType: string,
        assetId: string,
    }): CancelablePromise<ApiResponse_list_AssetVersionRead__> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/projects/{project_id}/assets/{asset_type}/{asset_id}/versions',
            path: {
                'project_id': projectId,
                'asset_type': assetType,
                'asset_id': assetId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 创建资产衍生版本
     * @returns ApiResponse_AssetProfileRead_ Successful Response
     * @throws ApiError
     */
    public static createAssetVersionApiApiV1StudioProjectsProjectIdAssetsAssetTypeAssetIdVersionsPost({
        projectId,
        assetType,
        assetId,
        requestBody,
    }: {
        projectId: string,
        assetType: string,
        assetId: string,
        requestBody: CreateDerivedVersionRequest,
    }): CancelablePromise<ApiResponse_AssetProfileRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/projects/{project_id}/assets/{asset_type}/{asset_id}/versions',
            path: {
                'project_id': projectId,
                'asset_type': assetType,
                'asset_id': assetId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 创建新的角色身份草稿版本
     * @returns ApiResponse_AssetProfileRead_ Successful Response
     * @throws ApiError
     */
    public static createCharacterIdentityVersionApiApiV1StudioProjectsProjectIdAssetsCharacterAssetIdIdentityVersionsPost({
        projectId,
        assetId,
        requestBody,
    }: {
        projectId: string,
        assetId: string,
        requestBody: CreateDerivedVersionRequest,
    }): CancelablePromise<ApiResponse_AssetProfileRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/projects/{project_id}/assets/character/{asset_id}/identity-versions',
            path: {
                'project_id': projectId,
                'asset_id': assetId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 切换当前资产/身份版本
     * @returns ApiResponse_AssetProfileRead_ Successful Response
     * @throws ApiError
     */
    public static switchAssetVersionApiApiV1StudioProjectsProjectIdAssetsAssetTypeAssetIdVersionsVersionIdSwitchPost({
        projectId,
        assetType,
        assetId,
        versionId,
        requestBody,
    }: {
        projectId: string,
        assetType: string,
        assetId: string,
        versionId: string,
        requestBody: SwitchVersionRequest,
    }): CancelablePromise<ApiResponse_AssetProfileRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/projects/{project_id}/assets/{asset_type}/{asset_id}/versions/{version_id}/switch',
            path: {
                'project_id': projectId,
                'asset_type': assetType,
                'asset_id': assetId,
                'version_id': versionId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 删除未引用的草稿版本
     * @returns ApiResponse_NoneType_ Successful Response
     * @throws ApiError
     */
    public static deleteAssetVersionApiApiV1StudioProjectsProjectIdAssetsAssetTypeAssetIdVersionsVersionIdDelete({
        projectId,
        assetType,
        assetId,
        versionId,
    }: {
        projectId: string,
        assetType: string,
        assetId: string,
        versionId: string,
    }): CancelablePromise<ApiResponse_NoneType_> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/studio/projects/{project_id}/assets/{asset_type}/{asset_id}/versions/{version_id}',
            path: {
                'project_id': projectId,
                'asset_type': assetType,
                'asset_id': assetId,
                'version_id': versionId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 资产图片候选列表
     * @returns ApiResponse_list_AssetImageCandidateRead__ Successful Response
     * @throws ApiError
     */
    public static listAssetCandidatesApiApiV1StudioProjectsProjectIdAssetsAssetTypeAssetIdCandidatesGet({
        projectId,
        assetType,
        assetId,
        viewAngle,
    }: {
        projectId: string,
        assetType: string,
        assetId: string,
        viewAngle?: (string | null),
    }): CancelablePromise<ApiResponse_list_AssetImageCandidateRead__> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/projects/{project_id}/assets/{asset_type}/{asset_id}/candidates',
            path: {
                'project_id': projectId,
                'asset_type': assetType,
                'asset_id': assetId,
            },
            query: {
                'view_angle': viewAngle,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 生成资产候选图（默认两张）
     * @returns ApiResponse_list_AssetImageCandidateRead__ Successful Response
     * @throws ApiError
     */
    public static generateAssetCandidatesApiApiV1StudioProjectsProjectIdAssetsAssetTypeAssetIdCandidatesGeneratePost({
        projectId,
        assetType,
        assetId,
        requestBody,
    }: {
        projectId: string,
        assetType: string,
        assetId: string,
        requestBody: GenerateCandidatesRequest,
    }): CancelablePromise<ApiResponse_list_AssetImageCandidateRead__> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/projects/{project_id}/assets/{asset_type}/{asset_id}/candidates/generate',
            path: {
                'project_id': projectId,
                'asset_type': assetType,
                'asset_id': assetId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 上传资产图片候选
     * @returns ApiResponse_AssetProfileRead_ Successful Response
     * @throws ApiError
     */
    public static uploadAssetCandidateApiApiV1StudioProjectsProjectIdAssetsAssetTypeAssetIdCandidatesUploadPost({
        projectId,
        assetType,
        assetId,
        formData,
        viewAngle = 'front',
        versionId,
    }: {
        projectId: string,
        assetType: string,
        assetId: string,
        formData: Body_upload_asset_candidate_api_api_v1_studio_projects__project_id__assets__asset_type___asset_id__candidates_upload_post,
        viewAngle?: string,
        versionId?: (string | null),
    }): CancelablePromise<ApiResponse_AssetProfileRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/projects/{project_id}/assets/{asset_type}/{asset_id}/candidates/upload',
            path: {
                'project_id': projectId,
                'asset_type': assetType,
                'asset_id': assetId,
            },
            query: {
                'view_angle': viewAngle,
                'version_id': versionId,
            },
            formData: formData,
            mediaType: 'multipart/form-data',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 采纳资产图片候选
     * @returns ApiResponse_AssetProfileRead_ Successful Response
     * @throws ApiError
     */
    public static adoptAssetCandidateApiApiV1StudioProjectsProjectIdAssetsAssetTypeAssetIdCandidatesCandidateIdAdoptPost({
        projectId,
        assetType,
        assetId,
        candidateId,
        requestBody,
    }: {
        projectId: string,
        assetType: string,
        assetId: string,
        candidateId: number,
        requestBody: CandidateAdoptRequest,
    }): CancelablePromise<ApiResponse_AssetProfileRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/projects/{project_id}/assets/{asset_type}/{asset_id}/candidates/{candidate_id}/adopt',
            path: {
                'project_id': projectId,
                'asset_type': assetType,
                'asset_id': assetId,
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
     * 删除未采纳候选图
     * @returns ApiResponse_AssetProfileRead_ Successful Response
     * @throws ApiError
     */
    public static deleteAssetCandidateApiApiV1StudioProjectsProjectIdAssetsAssetTypeAssetIdCandidatesCandidateIdDelete({
        projectId,
        assetType,
        assetId,
        candidateId,
    }: {
        projectId: string,
        assetType: string,
        assetId: string,
        candidateId: number,
    }): CancelablePromise<ApiResponse_AssetProfileRead_> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/studio/projects/{project_id}/assets/{asset_type}/{asset_id}/candidates/{candidate_id}',
            path: {
                'project_id': projectId,
                'asset_type': assetType,
                'asset_id': assetId,
                'candidate_id': candidateId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 锁定角色视觉身份
     * @returns ApiResponse_AssetProfileRead_ Successful Response
     * @throws ApiError
     */
    public static lockCharacterIdentityApiApiV1StudioProjectsProjectIdAssetsCharacterAssetIdLockPost({
        projectId,
        assetId,
        requestBody,
    }: {
        projectId: string,
        assetId: string,
        requestBody: CharacterLockRequest,
    }): CancelablePromise<ApiResponse_AssetProfileRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/projects/{project_id}/assets/character/{asset_id}/lock',
            path: {
                'project_id': projectId,
                'asset_id': assetId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 角色音色绑定与最终生效来源
     * @returns ApiResponse_VoiceBindingRead_ Successful Response
     * @throws ApiError
     */
    public static getCharacterVoiceApiApiV1StudioProjectsProjectIdAssetsCharacterAssetIdVoiceGet({
        projectId,
        assetId,
    }: {
        projectId: string,
        assetId: string,
    }): CancelablePromise<ApiResponse_VoiceBindingRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/projects/{project_id}/assets/character/{asset_id}/voice',
            path: {
                'project_id': projectId,
                'asset_id': assetId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 绑定/修改/解除角色音色
     * @returns ApiResponse_VoiceBindingRead_ Successful Response
     * @throws ApiError
     */
    public static updateCharacterVoiceApiApiV1StudioProjectsProjectIdAssetsCharacterAssetIdVoicePatch({
        projectId,
        assetId,
        requestBody,
    }: {
        projectId: string,
        assetId: string,
        requestBody: VoiceBindingUpdate,
    }): CancelablePromise<ApiResponse_VoiceBindingRead_> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/studio/projects/{project_id}/assets/character/{asset_id}/voice',
            path: {
                'project_id': projectId,
                'asset_id': assetId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
