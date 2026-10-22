/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiResponse_ScriptDocumentListRead_ } from '../models/ApiResponse_ScriptDocumentListRead_';
import type { ApiResponse_ScriptDocumentRead_ } from '../models/ApiResponse_ScriptDocumentRead_';
import type { ApiResponse_ScriptDocumentUploadRead_ } from '../models/ApiResponse_ScriptDocumentUploadRead_';
import type { ApiResponse_ScriptDocumentVersionDetailRead_ } from '../models/ApiResponse_ScriptDocumentVersionDetailRead_';
import type { Body_upload_episode_document_api_api_v1_studio_projects__project_id__chapters__chapter_id__script_document_post } from '../models/Body_upload_episode_document_api_api_v1_studio_projects__project_id__chapters__chapter_id__script_document_post';
import type { Body_upload_worldbuilding_document_api_api_v1_studio_projects__project_id__script_documents_worldbuilding_post } from '../models/Body_upload_worldbuilding_document_api_api_v1_studio_projects__project_id__script_documents_worldbuilding_post';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class StudioScriptDocumentsService {
    /**
     * 项目剧本文档列表
     * @returns ApiResponse_ScriptDocumentListRead_ Successful Response
     * @throws ApiError
     */
    public static listScriptDocumentsApiApiV1StudioProjectsProjectIdScriptDocumentsGet({
        projectId,
    }: {
        projectId: string,
    }): CancelablePromise<ApiResponse_ScriptDocumentListRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/projects/{project_id}/script-documents',
            path: {
                'project_id': projectId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 上传世界观与人物设定文档
     * @returns ApiResponse_ScriptDocumentUploadRead_ Successful Response
     * @throws ApiError
     */
    public static uploadWorldbuildingDocumentApiApiV1StudioProjectsProjectIdScriptDocumentsWorldbuildingPost({
        projectId,
        formData,
    }: {
        projectId: string,
        formData: Body_upload_worldbuilding_document_api_api_v1_studio_projects__project_id__script_documents_worldbuilding_post,
    }): CancelablePromise<ApiResponse_ScriptDocumentUploadRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/projects/{project_id}/script-documents/worldbuilding',
            path: {
                'project_id': projectId,
            },
            formData: formData,
            mediaType: 'multipart/form-data',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 上传某一集剧本文件
     * @returns ApiResponse_ScriptDocumentUploadRead_ Successful Response
     * @throws ApiError
     */
    public static uploadEpisodeDocumentApiApiV1StudioProjectsProjectIdChaptersChapterIdScriptDocumentPost({
        projectId,
        chapterId,
        formData,
    }: {
        projectId: string,
        chapterId: string,
        formData: Body_upload_episode_document_api_api_v1_studio_projects__project_id__chapters__chapter_id__script_document_post,
    }): CancelablePromise<ApiResponse_ScriptDocumentUploadRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/projects/{project_id}/chapters/{chapter_id}/script-document',
            path: {
                'project_id': projectId,
                'chapter_id': chapterId,
            },
            formData: formData,
            mediaType: 'multipart/form-data',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 剧本文档详情与版本列表
     * @returns ApiResponse_ScriptDocumentRead_ Successful Response
     * @throws ApiError
     */
    public static getScriptDocumentApiApiV1StudioScriptDocumentsDocumentIdGet({
        documentId,
    }: {
        documentId: string,
    }): CancelablePromise<ApiResponse_ScriptDocumentRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/script-documents/{document_id}',
            path: {
                'document_id': documentId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 读取文档版本原文
     * @returns ApiResponse_ScriptDocumentVersionDetailRead_ Successful Response
     * @throws ApiError
     */
    public static getScriptDocumentVersionApiApiV1StudioScriptDocumentsDocumentIdVersionsVersionIdGet({
        documentId,
        versionId,
    }: {
        documentId: string,
        versionId: string,
    }): CancelablePromise<ApiResponse_ScriptDocumentVersionDetailRead_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/script-documents/{document_id}/versions/{version_id}',
            path: {
                'document_id': documentId,
                'version_id': versionId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 启用某个文档版本并同步章节原文
     * @returns ApiResponse_ScriptDocumentRead_ Successful Response
     * @throws ApiError
     */
    public static activateScriptDocumentVersionApiApiV1StudioScriptDocumentsDocumentIdVersionsVersionIdActivatePost({
        documentId,
        versionId,
    }: {
        documentId: string,
        versionId: string,
    }): CancelablePromise<ApiResponse_ScriptDocumentRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/script-documents/{document_id}/versions/{version_id}/activate',
            path: {
                'document_id': documentId,
                'version_id': versionId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
