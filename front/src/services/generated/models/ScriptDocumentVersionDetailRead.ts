/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 单版本完整原文，用于并排审核与证据定位。
 */
export type ScriptDocumentVersionDetailRead = {
    id: string;
    document_id: string;
    version_no: number;
    file_id?: (string | null);
    file_name?: string;
    file_type?: string;
    content_hash?: string;
    text_length?: number;
    status?: string;
    parse_status?: string;
    extract_meta?: Record<string, any>;
    created_at?: (string | null);
    raw_text?: string;
};

