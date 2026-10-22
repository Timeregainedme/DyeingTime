/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 接受/忽略差异报告；不会自动覆盖正式业务数据。
 */
export type ScriptDiffDecisionRequest = {
    /**
     * accepted / ignored
     */
    status: string;
    decisions?: Record<string, any>;
};

