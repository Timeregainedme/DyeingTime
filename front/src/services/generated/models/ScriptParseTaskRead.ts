/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ScriptParseRunRead } from './ScriptParseRunRead';
/**
 * 开始解析的返回：run 状态 + 是否复用。
 */
export type ScriptParseTaskRead = {
    run: ScriptParseRunRead;
    reused?: boolean;
};

