/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ScriptParseCandidateRead } from './ScriptParseCandidateRead';
export type ScriptParseRunRead = {
    id: string;
    document_id: string;
    version_id: string;
    worldbuilding_version_id?: (string | null);
    task_id?: (string | null);
    status: string;
    progress?: number;
    model_id?: (string | null);
    model_name?: string;
    provider_name?: string;
    prompt_version?: string;
    prompt_hash?: string;
    chunk_count?: number;
    failed_chunks?: Array<number>;
    error?: string;
    started_at?: (string | null);
    finished_at?: (string | null);
    confirmed_at?: (string | null);
    confirmed_by?: (number | null);
    applied_summary?: (Record<string, any> | null);
    confirmed_result?: (Record<string, any> | null);
    candidates?: Array<ScriptParseCandidateRead>;
    created_at?: (string | null);
    updated_at?: (string | null);
};

