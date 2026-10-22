/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AssetImpactShot } from './AssetImpactShot';
export type AssetImpactRead = {
    project_id: string;
    asset_type: string;
    asset_id: string;
    from_version_id?: (string | null);
    to_version_id?: (string | null);
    chapters?: Array<Record<string, any>>;
    shots?: Array<AssetImpactShot>;
    summary?: Record<string, any>;
    notes?: Array<string>;
};

