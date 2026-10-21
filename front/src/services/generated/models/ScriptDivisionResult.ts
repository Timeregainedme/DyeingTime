/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ShotDivision } from './ShotDivision';
/**
 * 剧本分镜结果：镜头列表（每镜起止行号+预览文本）。
 */
export type ScriptDivisionResult = {
    /**
     * 分镜列表
     */
    shots?: Array<ShotDivision>;
    /**
     * 总镜头数
     */
    total_shots: number;
    /**
     * 拆分说明或建议（可选）
     */
    notes?: (string | null);
};

