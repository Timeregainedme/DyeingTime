/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { StyleStructuredProfile } from './StyleStructuredProfile';
/**
 * 风格目录项。
 */
export type ProjectStyleOptionRead = {
    id: string;
    /**
     * 所属画面表现形式（现实/动漫…）
     */
    visual_style: string;
    /**
     * 风格名称
     */
    name: string;
    /**
     * 面向用户的说明
     */
    description?: string;
    /**
     * 提示词质感描述（注入到出图提示词）
     */
    prompt_pack?: string;
    /**
     * 同组内排序
     */
    sort_order?: number;
    /**
     * AI 分析/人工修订的结构化风格字段
     */
    structured_profile?: (StyleStructuredProfile | null);
    /**
     * 风格参考图文件 ID
     */
    reference_file_ids?: Array<string>;
    /**
     * 已确认样张文件 ID
     */
    sample_file_ids?: Array<string>;
    /**
     * AI 分析状态：draft / analyzed
     */
    analysis_status?: string;
    /**
     * 是否平台内置模板
     */
    is_builtin?: boolean;
};

