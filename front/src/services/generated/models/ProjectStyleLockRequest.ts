/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 锁定风格；不传 style_id 时使用当前选择。
 */
export type ProjectStyleLockRequest = {
    style_id?: (string | null);
    /**
     * 确认样张文件 ID（最多 3 张）
     */
    sample_file_ids?: Array<string>;
};

