/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 默认一次生成两张；不提供无界重试。
 */
export type GenerateCandidatesRequest = {
    view_angle?: 'front' | 'left' | 'right' | 'back' | 'three_quarter';
    candidate_count?: number;
    /**
     * 可选：覆盖资产图提示词
     */
    prompt?: (string | null);
};

