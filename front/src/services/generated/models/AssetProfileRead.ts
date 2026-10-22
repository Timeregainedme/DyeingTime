/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AssetImageCandidateRead } from './AssetImageCandidateRead';
import type { AssetVersionRead } from './AssetVersionRead';
import type { CharacterAliasRead } from './CharacterAliasRead';
export type AssetProfileRead = {
    project_id: string;
    asset_type: string;
    asset_id: string;
    name: string;
    description?: string;
    style?: string;
    visual_style?: string;
    tags?: Array<string>;
    thumbnail?: string;
    current_version_id?: (string | null);
    versions?: Array<AssetVersionRead>;
    candidates?: Array<AssetImageCandidateRead>;
    age_range?: string;
    appearance?: string;
    face_features?: string;
    body_type?: string;
    identity_features?: string;
    aliases?: Array<CharacterAliasRead>;
    identity_version_id?: (string | null);
    current_appearance_version_id?: (string | null);
    identity_locked_at?: (string | null);
    identity_lock_version?: number;
    identity_locked?: boolean;
    voice_id?: (string | null);
    voice_source?: (string | null);
    voice_description?: string;
    effective_voice_id?: (string | null);
    effective_voice_source?: (string | null);
    voice_bound_at?: (string | null);
};

