/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ProjectVisualStyle } from './ProjectVisualStyle';
export type ProjectRead = {
    /**
     * 项目名称
     */
    name: string;
    /**
     * 项目简介
     */
    description?: string;
    /**
     * 题材/风格（来自项目风格目录）
     */
    style: string;
    /**
     * 画面表现形式
     */
    visual_style?: ProjectVisualStyle;
    /**
     * 随机种子
     */
    seed?: number;
    /**
     * 是否统一风格
     */
    unify_style?: boolean;
    /**
     * 进度百分比（0-100）
     */
    progress?: number;
    /**
     * 项目级默认视频比例；分镜未覆盖时生效
     */
    default_video_ratio?: (string | null);
    /**
     * 项目级默认图片比例；为空时回落到视频比例
     */
    default_image_ratio?: (string | null);
    /**
     * 项目级默认图片分辨率档位（standard/high）；为空时回落到提供方默认档位
     */
    default_image_resolution_profile?: (string | null);
    /**
     * 项目级默认视频分辨率档位（如 768p/2k）；为空时回落到提供方默认档位
     */
    default_video_resolution?: (string | null);
    /**
     * 视频生成时是否自动带上镜头台词已生成的配音作为参考音频（true=使用，false=纯画面参考）；新项目默认关闭
     */
    use_dialog_audio_as_reference?: boolean;
    /**
     * 聚合统计（JSON）
     */
    stats?: Record<string, any>;
    id: string;
    /**
     * 所属工作区 ID
     */
    workspace_id: string;
    /**
     * 创建者账号 ID
     */
    created_by?: (number | null);
    /**
     * 项目默认图片模型 ID
     */
    default_image_model_id?: (string | null);
    /**
     * 项目默认视频模型 ID
     */
    default_video_model_id?: (string | null);
    /**
     * 项目默认音频模型 ID
     */
    default_audio_model_id?: (string | null);
    /**
     * 默认参考模式
     */
    default_reference_mode?: (string | null);
    /**
     * 默认镜头时长（秒）
     */
    default_shot_duration?: (number | null);
    /**
     * 项目业务时长下限（秒）
     */
    video_duration_min?: (number | null);
    /**
     * 项目业务时长上限（秒）
     */
    video_duration_max?: (number | null);
    /**
     * 视频批量并发数
     */
    video_concurrency?: (number | null);
    /**
     * 生成配置版本
     */
    generation_config_version?: (number | null);
    /**
     * 生成配置确认时间；为空表示未确认
     */
    generation_config_confirmed_at?: (string | null);
    /**
     * 生成配置最近保存时间
     */
    generation_config_updated_at?: (string | null);
};

