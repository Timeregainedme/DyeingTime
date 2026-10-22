/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 保存项目生成配置。
 *
 * `confirm=true` 时写入快照并递增版本；`confirm=false` 只保存草稿。
 * 模型字段显式传 null 表示清除项目覆盖、回退全局默认。
 */
export type ProjectGenerationConfigUpdate = {
    default_image_model_id?: (string | null);
    default_video_model_id?: (string | null);
    default_audio_model_id?: (string | null);
    default_video_ratio?: (string | null);
    default_video_resolution?: (string | null);
    default_image_ratio?: (string | null);
    default_image_resolution_profile?: (string | null);
    default_shot_duration?: (number | null);
    video_duration_min?: (number | null);
    video_duration_max?: (number | null);
    video_concurrency?: (number | null);
    default_reference_mode?: (string | null);
    use_dialog_audio_as_reference?: (boolean | null);
    /**
     * 是否确认并写入配置快照
     */
    confirm?: boolean;
};

