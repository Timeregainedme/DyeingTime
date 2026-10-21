/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 分镜帧 guidance 的保留/压缩决策结果。
 */
export type FrameGuidanceDecisionRead = {
    /**
     * guidance 原文
     */
    text: string;
    /**
     * guidance 分类，如 summary / continuity / composition / screen
     */
    category: string;
    /**
     * 简短原因标签，如 首帧保空间 / 关键帧保轴线
     */
    reason_tag?: string;
    /**
     * 该 guidance 被保留或压缩的原因说明
     */
    reason: string;
};

