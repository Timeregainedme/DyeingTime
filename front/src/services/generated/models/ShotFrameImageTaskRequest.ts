/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ShotFrameType } from './ShotFrameType';
import type { ShotLinkedAssetItem } from './ShotLinkedAssetItem';
/**
 * 镜头分镜帧图片生成请求体：只根据 `shot_id + frame_type` 定位 ShotFrameImage。
 *
 * 用于替代旧接口中通过 `image_id` 直接传入 ShotFrameImage.id 的方式。
 */
export type ShotFrameImageTaskRequest = {
    /**
     * 可选模型 ID（models.id）；不传则使用 ModelSettings.default_image_model_id；Provider 由模型关联反查
     */
    model_id?: (string | null);
    /**
     * first | last | key
     */
    frame_type: ShotFrameType;
    /**
     * 提示词（由前端传入，创建任务接口必填）。
     */
    prompt: string;
    /**
     * 参考资产条目列表（可多张，顺序有效）。后端会使用 item.file_id 作为参考图；无效条目会被跳过。
     */
    images?: Array<ShotLinkedAssetItem>;
    /**
     * 目标视频画幅比例；关键帧将按该画幅生成，以提升后续视频参考稳定性
     */
    target_ratio: '16:9' | '4:3' | '1:1' | '3:4' | '9:16' | '21:9' | '3:2' | '2:3';
    /**
     * 关键帧输出分辨率档位，默认 standard
     */
    resolution_profile?: ('standard' | 'high' | null);
};

