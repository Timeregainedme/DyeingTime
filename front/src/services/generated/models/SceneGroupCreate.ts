/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type SceneGroupCreate = {
    title?: string;
    description?: string;
    location?: string;
    time_of_day?: string;
    story_event?: string;
    primary_scene_id?: (string | null);
    /**
     * 不传则追加到末尾
     */
    index?: (number | null);
};

