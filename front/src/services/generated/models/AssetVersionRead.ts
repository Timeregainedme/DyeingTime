/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type AssetVersionRead = {
    id: string;
    project_id: string;
    asset_type: string;
    asset_id: string;
    version_no: number;
    parent_version_id?: (string | null);
    version_kind: string;
    variant_type: string;
    name?: string;
    description?: string;
    attributes?: Record<string, any>;
    source?: string;
    status?: string;
    created_at?: (string | null);
    adopted_image_count?: number;
};

