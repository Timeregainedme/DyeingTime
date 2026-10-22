/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 风格的结构化描述；AI 分析输出与人工修订共用同一形状。
 */
export type StyleStructuredProfile = {
    /**
     * 视觉媒介
     */
    medium?: string;
    /**
     * 画面质感
     */
    texture?: string;
    /**
     * 色彩与饱和度
     */
    color?: string;
    /**
     * 光照方式
     */
    lighting?: string;
    /**
     * 材质特征
     */
    material?: string;
    /**
     * 人物渲染特征
     */
    character_rendering?: string;
    /**
     * 场景渲染特征
     */
    scene_rendering?: string;
    /**
     * 摄影与运镜风格
     */
    camera?: string;
    /**
     * 应当保持的视觉特征
     */
    keep?: string;
    /**
     * 禁止出现的风格特征
     */
    avoid?: string;
};

