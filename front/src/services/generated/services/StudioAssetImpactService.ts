/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiResponse_AssetImpactRead_ } from '../models/ApiResponse_AssetImpactRead_';
import type { ApiResponse_list_AssetVersionImpactRefRead__ } from '../models/ApiResponse_list_AssetVersionImpactRefRead__';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class StudioAssetImpactService {
    /**
     * 资产引用与受影响镜头
     * @returns ApiResponse_AssetImpactRead_ Successful Response
     * @throws ApiError
     */
    public static getAssetImpactApiApiV1StudioProjectsProjectIdAssetsAssetTypeAssetIdImpactGet({
        projectId,
        assetType,
        assetId,
        fromVersionId,
        toVersionId,
    }: {
        projectId: string,
        assetType: string,
        assetId: string,
        fromVersionId?: (string | null),
        toVersionId?: (string | null),
    }): CancelablePromise<ApiResponse_AssetImpactRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/projects/{project_id}/assets/{asset_type}/{asset_id}/impact',
            path: {
                'project_id': projectId,
                'asset_type': assetType,
                'asset_id': assetId,
            },
            query: {
                'from_version_id': fromVersionId,
                'to_version_id': toVersionId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 资产版本切换影响历史
     * @returns ApiResponse_list_AssetVersionImpactRefRead__ Successful Response
     * @throws ApiError
     */
    public static listAssetImpactHistoryApiApiV1StudioProjectsProjectIdAssetsAssetTypeAssetIdImpactHistoryGet({
        projectId,
        assetType,
        assetId,
    }: {
        projectId: string,
        assetType: string,
        assetId: string,
    }): CancelablePromise<ApiResponse_list_AssetVersionImpactRefRead__> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/projects/{project_id}/assets/{asset_type}/{asset_id}/impact-history',
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
}
