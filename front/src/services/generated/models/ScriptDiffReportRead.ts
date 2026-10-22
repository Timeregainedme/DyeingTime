/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ScriptDiffReportRead = {
    id: string;
    document_id: string;
    old_version_id: string;
    new_version_id: string;
    status?: string;
    text_diff?: Array<Record<string, any>>;
    structured_diff?: Record<string, any>;
    impact?: Record<string, any>;
    decisions?: Record<string, any>;
    decided_by?: (number | null);
    decided_at?: (string | null);
    created_at?: (string | null);
    updated_at?: (string | null);
};

