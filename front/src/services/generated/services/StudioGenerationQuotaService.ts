/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiResponse_list_QuotaReservationRead__ } from '../models/ApiResponse_list_QuotaReservationRead__';
import type { ApiResponse_list_QuotaStatusRead__ } from '../models/ApiResponse_list_QuotaStatusRead__';
import type { ApiResponse_QuotaReservationRead_ } from '../models/ApiResponse_QuotaReservationRead_';
import type { QuotaReserveRequest } from '../models/QuotaReserveRequest';
import type { QuotaSettleRequest } from '../models/QuotaSettleRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class StudioGenerationQuotaService {
    /**
     * 查询 V2 验收测试额度
     * @returns ApiResponse_list_QuotaStatusRead__ Successful Response
     * @throws ApiError
     */
    public static getGenerationQuotaApiApiV1StudioGenerationQuotaGet({
        scope = 'v2-acceptance',
    }: {
        scope?: string,
    }): CancelablePromise<ApiResponse_list_QuotaStatusRead__> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/generation-quota',
            query: {
                'scope': scope,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 额度预留/结算记录
     * @returns ApiResponse_list_QuotaReservationRead__ Successful Response
     * @throws ApiError
     */
    public static listGenerationQuotaReservationsApiApiV1StudioGenerationQuotaReservationsGet({
        scope = 'v2-acceptance',
    }: {
        scope?: string,
    }): CancelablePromise<ApiResponse_list_QuotaReservationRead__> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/generation-quota/reservations',
            query: {
                'scope': scope,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 原子预留测试额度（防并发超额）
     * @returns ApiResponse_QuotaReservationRead_ Successful Response
     * @throws ApiError
     */
    public static reserveGenerationQuotaApiApiV1StudioGenerationQuotaReservePost({
        requestBody,
    }: {
        requestBody: QuotaReserveRequest,
    }): CancelablePromise<ApiResponse_QuotaReservationRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/generation-quota/reserve',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 结算测试额度预留
     * @returns ApiResponse_QuotaReservationRead_ Successful Response
     * @throws ApiError
     */
    public static settleGenerationQuotaApiApiV1StudioGenerationQuotaSettlePost({
        requestBody,
    }: {
        requestBody: QuotaSettleRequest,
    }): CancelablePromise<ApiResponse_QuotaReservationRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/generation-quota/settle',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
