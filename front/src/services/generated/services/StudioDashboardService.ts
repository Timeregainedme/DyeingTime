/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiResponse_DashboardRead_ } from '../models/ApiResponse_DashboardRead_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class StudioDashboardService {
    /**
     * 获取创作工作台首页聚合数据
     * 一次返回项目、章节、镜头、任务与待审核快照（按当前工作区隔离）。
     * @returns ApiResponse_DashboardRead_ Successful Response
     * @throws ApiError
     */
    public static getDashboardApiApiV1StudioDashboardGet(): CancelablePromise<ApiResponse_DashboardRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/dashboard',
        });
    }
}
