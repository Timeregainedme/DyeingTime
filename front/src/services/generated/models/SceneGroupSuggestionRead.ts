/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { SceneBeatSuggestion } from './SceneBeatSuggestion';
export type SceneGroupSuggestionRead = {
    chapter_id: string;
    parse_run_id?: (string | null);
    source_script_version_id?: (string | null);
    current_active_version_id?: (string | null);
    script_version_changed?: boolean;
    existing_group_count?: number;
    items?: Array<SceneBeatSuggestion>;
    warnings?: Array<string>;
};

