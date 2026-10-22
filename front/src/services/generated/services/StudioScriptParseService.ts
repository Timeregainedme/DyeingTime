/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiResponse_list_ScriptParseRunRead__ } from '../models/ApiResponse_list_ScriptParseRunRead__';
import type { ApiResponse_ScriptDiffReportRead_ } from '../models/ApiResponse_ScriptDiffReportRead_';
import type { ApiResponse_ScriptParseCandidateRead_ } from '../models/ApiResponse_ScriptParseCandidateRead_';
import type { ApiResponse_ScriptParseConfirmRead_ } from '../models/ApiResponse_ScriptParseConfirmRead_';
import type { ApiResponse_ScriptParseRunRead_ } from '../models/ApiResponse_ScriptParseRunRead_';
import type { ApiResponse_ScriptParseTaskRead_ } from '../models/ApiResponse_ScriptParseTaskRead_';
import type { ScriptDiffDecisionRequest } from '../models/ScriptDiffDecisionRequest';
import type { ScriptDiffRequest } from '../models/ScriptDiffRequest';
import type { ScriptParseCandidateCreate } from '../models/ScriptParseCandidateCreate';
import type { ScriptParseCandidateUpdate } from '../models/ScriptParseCandidateUpdate';
import type { ScriptParseMergeRequest } from '../models/ScriptParseMergeRequest';
import type { ScriptParseRequest } from '../models/ScriptParseRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class StudioScriptParseService {
    /**
     * 开始解析某一集剧本
     * @returns ApiResponse_ScriptParseTaskRead_ Successful Response
     * @throws ApiError
     */
    public static startScriptParseApiApiV1StudioScriptDocumentVersionsVersionIdParsePost({
        versionId,
        requestBody,
    }: {
        versionId: string,
        requestBody: ScriptParseRequest,
    }): CancelablePromise<ApiResponse_ScriptParseTaskRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/script-document-versions/{version_id}/parse',
            path: {
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
     * 解析运行详情与候选
     * @returns ApiResponse_ScriptParseRunRead_ Successful Response
     * @throws ApiError
     */
    public static getScriptParseRunApiApiV1StudioScriptParseRunsRunIdGet({
        runId,
    }: {
        runId: string,
    }): CancelablePromise<ApiResponse_ScriptParseRunRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/script-parse-runs/{run_id}',
            path: {
                'run_id': runId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 文档的解析运行历史
     * @returns ApiResponse_list_ScriptParseRunRead__ Successful Response
     * @throws ApiError
     */
    public static listScriptParseRunsApiApiV1StudioScriptDocumentsDocumentIdParseRunsGet({
        documentId,
    }: {
        documentId: string,
    }): CancelablePromise<ApiResponse_list_ScriptParseRunRead__> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/script-documents/{document_id}/parse-runs',
            path: {
                'document_id': documentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 编辑/接受/忽略解析候选
     * @returns ApiResponse_ScriptParseCandidateRead_ Successful Response
     * @throws ApiError
     */
    public static updateScriptParseCandidateApiApiV1StudioScriptParseRunsRunIdCandidatesCandidateIdPatch({
        runId,
        candidateId,
        requestBody,
    }: {
        runId: string,
        candidateId: string,
        requestBody: ScriptParseCandidateUpdate,
    }): CancelablePromise<ApiResponse_ScriptParseCandidateRead_> {
        return __request(OpenAPI, {
            method: 'PATCH',
            url: '/api/v1/studio/script-parse-runs/{run_id}/candidates/{candidate_id}',
            path: {
                'run_id': runId,
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
     * 删除解析候选
     * @returns ApiResponse_ScriptParseRunRead_ Successful Response
     * @throws ApiError
     */
    public static deleteScriptParseCandidateApiApiV1StudioScriptParseRunsRunIdCandidatesCandidateIdDelete({
        runId,
        candidateId,
    }: {
        runId: string,
        candidateId: string,
    }): CancelablePromise<ApiResponse_ScriptParseRunRead_> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/studio/script-parse-runs/{run_id}/candidates/{candidate_id}',
            path: {
                'run_id': runId,
                'candidate_id': candidateId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 人工新增解析候选
     * @returns ApiResponse_ScriptParseCandidateRead_ Successful Response
     * @throws ApiError
     */
    public static createScriptParseCandidateApiApiV1StudioScriptParseRunsRunIdCandidatesPost({
        runId,
        requestBody,
    }: {
        runId: string,
        requestBody: ScriptParseCandidateCreate,
    }): CancelablePromise<ApiResponse_ScriptParseCandidateRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/script-parse-runs/{run_id}/candidates',
            path: {
                'run_id': runId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 合并重复候选
     * @returns ApiResponse_ScriptParseRunRead_ Successful Response
     * @throws ApiError
     */
    public static mergeScriptParseCandidatesApiApiV1StudioScriptParseRunsRunIdMergePost({
        runId,
        requestBody,
    }: {
        runId: string,
        requestBody: ScriptParseMergeRequest,
    }): CancelablePromise<ApiResponse_ScriptParseRunRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/script-parse-runs/{run_id}/merge',
            path: {
                'run_id': runId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 确认解析结果并写入正式数据
     * @returns ApiResponse_ScriptParseConfirmRead_ Successful Response
     * @throws ApiError
     */
    public static confirmScriptParseRunApiApiV1StudioScriptParseRunsRunIdConfirmPost({
        runId,
    }: {
        runId: string,
    }): CancelablePromise<ApiResponse_ScriptParseConfirmRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/script-parse-runs/{run_id}/confirm',
            path: {
                'run_id': runId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 生成版本差异报告
     * @returns ApiResponse_ScriptDiffReportRead_ Successful Response
     * @throws ApiError
     */
    public static createScriptDiffApiApiV1StudioScriptDocumentsDocumentIdDiffPost({
        documentId,
        requestBody,
    }: {
        documentId: string,
        requestBody: ScriptDiffRequest,
    }): CancelablePromise<ApiResponse_ScriptDiffReportRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/script-documents/{document_id}/diff',
            path: {
                'document_id': documentId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 差异报告详情
     * @returns ApiResponse_ScriptDiffReportRead_ Successful Response
     * @throws ApiError
     */
    public static getScriptDiffReportApiApiV1StudioScriptDiffReportsReportIdGet({
        reportId,
    }: {
        reportId: string,
    }): CancelablePromise<ApiResponse_ScriptDiffReportRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/script-diff-reports/{report_id}',
            path: {
                'report_id': reportId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 接受/忽略差异报告
     * @returns ApiResponse_ScriptDiffReportRead_ Successful Response
     * @throws ApiError
     */
    public static decideScriptDiffReportApiApiV1StudioScriptDiffReportsReportIdStatusPost({
        reportId,
        requestBody,
    }: {
        reportId: string,
        requestBody: ScriptDiffDecisionRequest,
    }): CancelablePromise<ApiResponse_ScriptDiffReportRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/script-diff-reports/{report_id}/status',
            path: {
                'report_id': reportId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
