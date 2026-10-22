/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type AssetVersionImpactRefRead = {
    id: number;
    project_id: string;
    asset_type: string;
    asset_id: string;
    from_version_id?: (string | null);
    to_version_id?: (string | null);
    shot_id: string;
    chapter_id: string;
    certainty: string;
    reference_kind: string;
    had_video?: boolean;
    created_at?: (string | null);
};

