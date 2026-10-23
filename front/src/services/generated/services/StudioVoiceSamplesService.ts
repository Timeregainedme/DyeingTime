/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApiResponse_list_VoiceSampleRead__ } from '../models/ApiResponse_list_VoiceSampleRead__';
import type { ApiResponse_NoneType_ } from '../models/ApiResponse_NoneType_';
import type { ApiResponse_VoiceSampleRead_ } from '../models/ApiResponse_VoiceSampleRead_';
import type { Body_upload_voice_sample_api_api_v1_studio_characters__character_id__voice_samples_post } from '../models/Body_upload_voice_sample_api_api_v1_studio_characters__character_id__voice_samples_post';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class StudioVoiceSamplesService {
    /**
     * 角色固定音色样本列表
     * @returns ApiResponse_list_VoiceSampleRead__ Successful Response
     * @throws ApiError
     */
    public static listVoiceSamplesApiApiV1StudioCharactersCharacterIdVoiceSamplesGet({
        characterId,
    }: {
        characterId: string,
    }): CancelablePromise<ApiResponse_list_VoiceSampleRead__> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/studio/characters/{character_id}/voice-samples',
            path: {
                'character_id': characterId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 上传角色固定音色样本
     * @returns ApiResponse_VoiceSampleRead_ Successful Response
     * @throws ApiError
     */
    public static uploadVoiceSampleApiApiV1StudioCharactersCharacterIdVoiceSamplesPost({
        characterId,
        formData,
    }: {
        characterId: string,
        formData: Body_upload_voice_sample_api_api_v1_studio_characters__character_id__voice_samples_post,
    }): CancelablePromise<ApiResponse_VoiceSampleRead_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/studio/characters/{character_id}/voice-samples',
            path: {
                'character_id': characterId,
            },
            formData: formData,
            mediaType: 'multipart/form-data',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 停用角色固定音色样本
     * @returns ApiResponse_NoneType_ Successful Response
     * @throws ApiError
     */
    public static deleteVoiceSampleApiApiV1StudioCharactersCharacterIdVoiceSamplesSampleIdDelete({
        characterId,
        sampleId,
    }: {
        characterId: string,
        sampleId: number,
    }): CancelablePromise<ApiResponse_NoneType_> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/studio/characters/{character_id}/voice-samples/{sample_id}',
            path: {
                'character_id': characterId,
                'sample_id': sampleId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
