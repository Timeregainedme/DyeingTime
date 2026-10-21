/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 剧本优化输出：仅在发现角色混淆问题时使用。
 */
export type ScriptOptimizationResult = {
    /**
     * 优化后的剧本文本
     */
    optimized_script_text: string;
    /**
     * 改动摘要（只围绕 issues）
     */
    change_summary: string;
};

