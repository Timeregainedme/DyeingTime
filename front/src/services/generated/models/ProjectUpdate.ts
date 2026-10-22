/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ProjectVisualStyle } from './ProjectVisualStyle';
export type ProjectUpdate = {
    name?: (string | null);
    description?: (string | null);
    /**
     * 题材/风格（来自项目风格目录）
     */
    style?: (string | null);
    visual_style?: (ProjectVisualStyle | null);
    seed?: (number | null);
    unify_style?: (boolean | null);
    progress?: (number | null);
    default_video_ratio?: (string | null);
    default_image_ratio?: (string | null);
    default_image_resolution_profile?: (string | null);
    default_video_resolution?: (string | null);
    use_dialog_audio_as_reference?: (boolean | null);
    stats?: (Record<string, any> | null);
};

