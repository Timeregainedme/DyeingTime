/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EvidenceSpan } from './EvidenceSpan';
/**
 * 实体变体条目（最小可用结构，便于服装/外形演变）。
 */
export type EntityVariant = {
    /**
     * 变体键（例如 outfit_v1、wounded_state 等）
     */
    variant_key: string;
    /**
     * 变体描述（简短）
     */
    description?: (string | null);
    /**
     * 涉及镜头序号
     */
    affected_shots?: Array<number>;
    /**
     * 原文依据（可选）
     */
    evidence?: Array<EvidenceSpan>;
};

