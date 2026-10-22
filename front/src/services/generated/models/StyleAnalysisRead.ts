/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { StyleStructuredProfile } from './StyleStructuredProfile';
/**
 * AI 输出的结构化风格字段；可直接保存为草稿。
 */
export type StyleAnalysisRead = {
    profile: StyleStructuredProfile;
    prompt_pack: string;
    model_id: string;
    model_name: string;
    provider_name: string;
    image_count: number;
};

