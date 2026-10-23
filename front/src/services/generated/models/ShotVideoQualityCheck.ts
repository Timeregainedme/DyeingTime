/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 视频生成质量检查项。
 *
 * 与 `ShotVideoReadinessCheck` 的区别：
 * - readiness check 回答“生成输入是否完整、能否提交”；
 * - quality check 回答“即使能提交，生成结果可能在哪里失真”，并区分
 * blocking / warning / info，避免把建议级别的提示误当成硬性阻塞。
 */
export type ShotVideoQualityCheck = {
    /**
     * 稳定规则编号
     */
    code: string;
    /**
     * 风险级别
     */
    level: 'blocking' | 'warning' | 'info';
    /**
     * 面向用户的解释
     */
    message: string;
    /**
     * 可执行的修复建议
     */
    fix_hint?: string;
};

