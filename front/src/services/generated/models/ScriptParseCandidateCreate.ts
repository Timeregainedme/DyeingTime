/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 人工新增一条候选。
 */
export type ScriptParseCandidateCreate = {
    /**
     * character / scene / prop / costume_change / scene_beat / dialogue / episode / issue
     */
    candidate_type: string;
    payload?: Record<string, any>;
    evidence?: Array<Record<string, any>>;
};

