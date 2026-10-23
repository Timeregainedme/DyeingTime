/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type SceneBeatSuggestion = {
    beat_key: string;
    index: number;
    title?: string;
    description?: string;
    location?: string;
    time_of_day?: string;
    story_event?: string;
    primary_scene_id?: (string | null);
    primary_scene_name?: string;
    source_start_char?: (number | null);
    source_end_char?: (number | null);
    already_imported?: boolean;
    evidence?: Array<Record<string, any>>;
};

