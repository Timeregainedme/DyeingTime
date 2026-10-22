/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 人工修改候选；只传需要改的字段。
 */
export type ScriptParseCandidateUpdate = {
    payload?: (Record<string, any> | null);
    /**
     * pending / edited / accepted / ignored
     */
    review_status?: (string | null);
    matched_entity_id?: (string | null);
    issue?: (string | null);
};

