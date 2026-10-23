/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ShotPlanDraftRead } from './ShotPlanDraftRead';
export type ShotPlanConfirmRead = {
    draft: ShotPlanDraftRead;
    shot_ids?: Array<string>;
    reused?: boolean;
    warnings?: Array<string>;
};

