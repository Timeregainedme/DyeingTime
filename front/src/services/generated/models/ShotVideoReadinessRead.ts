/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ShotVideoQualityCheck } from './ShotVideoQualityCheck';
import type { ShotVideoReadinessCheck } from './ShotVideoReadinessCheck';
/**
 * 镜头视频生成准备度。
 */
export type ShotVideoReadinessRead = {
    /**
     * 镜头 ID
     */
    shot_id: string;
    /**
     * 参考模式
     */
    reference_mode: string;
    /**
     * 是否满足当前 reference_mode 下的视频生成条件
     */
    ready: boolean;
    /**
     * 准备度检查项
     */
    checks?: Array<ShotVideoReadinessCheck>;
    /**
     * 生成质量风险；blocking 会阻止提交，warning/info 不阻塞
     */
    quality_checks?: Array<ShotVideoQualityCheck>;
};

