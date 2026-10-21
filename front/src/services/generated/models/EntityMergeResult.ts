/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EntityLibrary } from './EntityLibrary';
/**
 * 实体合并结果（脚本处理中间态）。
 */
export type EntityMergeResult = {
    /**
     * 合并后的实体库
     */
    merged_library: EntityLibrary;
    /**
     * 合并统计信息
     */
    merge_stats?: Record<string, any>;
    /**
     * 发现的冲突/待处理项
     */
    conflicts?: Array<string>;
    /**
     * 合并说明
     */
    notes?: (string | null);
};

