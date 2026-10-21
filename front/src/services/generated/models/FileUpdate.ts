/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { FileUsageWrite } from './FileUsageWrite';
export type FileUpdate = {
    name?: (string | null);
    thumbnail?: (string | null);
    tags?: (Array<string> | null);
    /**
     * 若提供则 upsert 一条 file_usages
     */
    usage?: (FileUsageWrite | null);
};

