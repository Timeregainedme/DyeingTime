/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EffectiveGenerationModelRead } from './EffectiveGenerationModelRead';
import type { ProjectGenerationConfigCheck } from './ProjectGenerationConfigCheck';
import type { ProjectGenerationOutputRead } from './ProjectGenerationOutputRead';
import type { ProjectGenerationPolicyRead } from './ProjectGenerationPolicyRead';
/**
 * 项目生成配置的完整只读视图。
 */
export type ProjectGenerationConfigRead = {
    project_id: string;
    confirmed: boolean;
    initialized: boolean;
    version: number;
    confirmed_at?: (string | null);
    updated_at?: (string | null);
    image_model: EffectiveGenerationModelRead;
    video_model: EffectiveGenerationModelRead;
    audio_model: EffectiveGenerationModelRead;
    output: ProjectGenerationOutputRead;
    policy: ProjectGenerationPolicyRead;
    checks?: Array<ProjectGenerationConfigCheck>;
    snapshot?: (Record<string, any> | null);
};

