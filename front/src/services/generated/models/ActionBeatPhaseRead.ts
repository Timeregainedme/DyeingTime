/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 动作拍点的轻量阶段推断结果。
 */
export type ActionBeatPhaseRead = {
    /**
     * 动作拍点原文
     */
    text: string;
    /**
     * 推断阶段：触发 / 峰值 / 收束
     */
    phase: 'trigger' | 'peak' | 'aftermath';
};

