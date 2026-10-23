/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { PromptReferenceRead } from './PromptReferenceRead';
export type PromptResolveRead = {
    prompt: string;
    resolved?: Array<PromptReferenceRead>;
    unresolved?: Array<string>;
    warnings?: Array<string>;
};

