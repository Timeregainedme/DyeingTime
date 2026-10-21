/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CostumeTimelineEntry } from './CostumeTimelineEntry';
/**
 * 单角色的服装演变时间线。
 */
export type CostumeTimeline = {
    /**
     * 角色稳定ID
     */
    character_id: string;
    /**
     * 角色名称
     */
    character_name: string;
    /**
     * 时间线条目
     */
    timeline_entries?: Array<CostumeTimelineEntry>;
};

