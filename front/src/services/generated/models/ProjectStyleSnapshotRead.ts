/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { StyleStructuredProfile } from './StyleStructuredProfile';
/**
 * 锁定快照；与全局风格目录解耦。
 */
export type ProjectStyleSnapshotRead = {
    project_id: string;
    source_style_id?: (string | null);
    style_name: string;
    visual_style: string;
    description: string;
    structured_profile?: (StyleStructuredProfile | null);
    prompt_pack: string;
    reference_file_ids?: Array<string>;
    sample_file_ids?: Array<string>;
    snapshot_version: number;
    locked_at: string;
};

