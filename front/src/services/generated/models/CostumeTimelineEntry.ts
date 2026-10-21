/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EvidenceSpan } from './EvidenceSpan';
/**
 * 单角色的服装演变时间线条目。
 */
export type CostumeTimelineEntry = {
    /**
     * 镜头序号
     */
    shot_index: number;
    /**
     * 可选：所属场景稳定ID（若已可推断）
     */
    scene_id?: (string | null);
    /**
     * 服装/外形要点（简短）
     */
    costume_note?: (string | null);
    /**
     * 与上一条相比的变化点
     */
    changes?: Array<string>;
    /**
     * 原文依据（可选）
     */
    evidence?: Array<EvidenceSpan>;
};

