/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 开始解析本集。
 */
export type ScriptParseRequest = {
    /**
     * 可选文本模型 ID；默认全局文本模型
     */
    model_id?: (string | null);
    /**
     * 已有完成的同输入解析时是否强制重新解析
     */
    force?: boolean;
};

