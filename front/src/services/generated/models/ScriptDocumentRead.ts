/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ScriptDocumentVersionRead } from './ScriptDocumentVersionRead';
/**
 * 剧本文档及其版本摘要。
 */
export type ScriptDocumentRead = {
    id: string;
    project_id: string;
    chapter_id?: (string | null);
    doc_type: string;
    title?: string;
    current_version_id?: (string | null);
    active_version_id?: (string | null);
    created_at?: (string | null);
    updated_at?: (string | null);
    versions?: Array<ScriptDocumentVersionRead>;
    current_version?: (ScriptDocumentVersionRead | null);
    active_version?: (ScriptDocumentVersionRead | null);
};

