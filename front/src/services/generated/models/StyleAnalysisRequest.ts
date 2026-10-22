/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 分析 1–3 张风格参考图；不落库。
 */
export type StyleAnalysisRequest = {
    /**
     * 风格参考图文件 ID
     */
    file_ids: Array<string>;
    /**
     * 可选文本/视觉模型 ID；默认使用全局文本模型
     */
    model_id?: (string | null);
};

