/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CostumeTimeline } from './CostumeTimeline';
import type { VariantSuggestion } from './VariantSuggestion';
/**
 * 变体分析结果。
 */
export type VariantAnalysisResult = {
    /**
     * 各角色服装演变时间线
     */
    costume_timelines?: Array<CostumeTimeline>;
    /**
     * 变体建议列表
     */
    variant_suggestions?: Array<VariantSuggestion>;
    /**
     * 章节变体建议
     */
    chapter_variants?: Record<string, Array<string>>;
    /**
     * 分析说明
     */
    notes?: (string | null);
};

