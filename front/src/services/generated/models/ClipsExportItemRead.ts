/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 预检查中的单个镜头导出项。
 */
export type ClipsExportItemRead = {
    shot_id: string;
    chapter_id: string;
    chapter_index: number;
    chapter_title?: string;
    scene_group_id?: (string | null);
    scene_index?: number;
    scene_title?: string;
    shot_index: number;
    title?: string;
    duration?: number;
    file_id?: (string | null);
    file_name: string;
    /**
     * ok/no_accepted/file_missing/storage_unavailable/unsupported_format
     */
    status?: string;
    size_bytes?: number;
    error?: string;
};

