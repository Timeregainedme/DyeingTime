/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EntityEntry } from './EntityEntry';
/**
 * 合并后的实体库（脚本处理中间态）。
 */
export type EntityLibrary = {
    /**
     * 角色库
     */
    characters?: Array<EntityEntry>;
    /**
     * 地点库
     */
    locations?: Array<EntityEntry>;
    /**
     * 场景库
     */
    scenes?: Array<EntityEntry>;
    /**
     * 道具库
     */
    props?: Array<EntityEntry>;
    /**
     * 总实体数
     */
    total_entries: number;
};

