/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { StyleStructuredProfile } from './StyleStructuredProfile';
/**
 * 修改风格（只改传入的字段）。
 */
export type ProjectStyleOptionUpdate = {
    name?: (string | null);
    description?: (string | null);
    prompt_pack?: (string | null);
    sort_order?: (number | null);
    structured_profile?: (StyleStructuredProfile | null);
    reference_file_ids?: (Array<string> | null);
    sample_file_ids?: (Array<string> | null);
    analysis_status?: (string | null);
};

