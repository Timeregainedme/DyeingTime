/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CameraAngle } from './CameraAngle';
import type { CameraMovement } from './CameraMovement';
import type { CameraShotType } from './CameraShotType';
/**
 * 镜头语义默认建议：用于准备阶段初始化镜头语言与动作拍点。
 */
export type ShotSemanticSuggestion = {
    /**
     * 建议景别
     */
    camera_shot?: (CameraShotType | null);
    /**
     * 建议机位
     */
    angle?: (CameraAngle | null);
    /**
     * 建议运镜
     */
    movement?: (CameraMovement | null);
    /**
     * 建议时长（秒）
     */
    duration?: (number | null);
    /**
     * 按时间顺序排列的动作拍点
     */
    action_beats?: Array<string>;
    /**
     * 不确定项说明
     */
    notes?: (string | null);
};

