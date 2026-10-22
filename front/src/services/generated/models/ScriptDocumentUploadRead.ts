/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ScriptDocumentRead } from './ScriptDocumentRead';
import type { ScriptDocumentVersionRead } from './ScriptDocumentVersionRead';
/**
 * 上传结果。``created=false`` 表示同内容重复上传，未新增版本。
 */
export type ScriptDocumentUploadRead = {
    document: ScriptDocumentRead;
    version: ScriptDocumentVersionRead;
    created: boolean;
    warnings?: Array<string>;
};

