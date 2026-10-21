/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EvidenceSpan } from './EvidenceSpan';
/**
 * 变体建议。
 */
export type VariantSuggestion = {
    /**
     * 实体ID
     */
    entity_id: string;
    /**
     * 实体名称
     */
    entity_name: string;
    /**
     * 实体类型（character/scene/prop/location）
     */
    entity_type: string;
    /**
     * 变体建议说明
     */
    suggestion: string;
    /**
     * 涉及的镜头
     */
    affected_shots?: Array<number>;
    /**
     * 原文依据（可选）
     */
    evidence?: Array<EvidenceSpan>;
};

