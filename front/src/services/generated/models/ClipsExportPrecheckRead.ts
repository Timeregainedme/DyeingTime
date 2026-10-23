/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ClipsExportItemRead } from './ClipsExportItemRead';
/**
 * 选择式 ZIP 导出的预检查结果。
 */
export type ClipsExportPrecheckRead = {
    project_id: string;
    project_name: string;
    selected_count: number;
    exportable_count: number;
    no_accepted_count: number;
    file_missing_count: number;
    unsupported_count: number;
    total_duration: number;
    estimated_size?: number;
    plan_hash: string;
    can_download: boolean;
    items?: Array<ClipsExportItemRead>;
    blockers?: Array<string>;
};

