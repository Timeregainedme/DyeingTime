/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 用于提示词渲染的镜头资产引用。
 */
export type ShotPromptAssetRef = {
    /**
     * 资产类型
     */
    type: 'character' | 'prop' | 'scene' | 'costume';
    /**
     * 资产名称
     */
    name: string;
    /**
     * 资产描述或提取候选描述
     */
    description?: string;
    /**
     * 可作为参考图的文件 ID
     */
    file_id?: (string | null);
    /**
     * 缩略图
     */
    thumbnail?: (string | null);
};

