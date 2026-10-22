/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 项目可选模型及其能力摘要。
 */
export type GenerationModelOptionRead = {
    id: string;
    name: string;
    category: string;
    provider_id: string;
    provider_name: string;
    provider_key?: string;
    provider_status?: string;
    /**
     * 模型类别与供应商是否都可用
     */
    available: boolean;
    unavailable_reason?: string;
    allowed_ratios?: Array<string>;
    default_ratio?: (string | null);
    allowed_resolutions?: Array<string>;
    default_resolution?: (string | null);
    ratio_size_profiles?: Record<string, Record<string, string>>;
    default_resolution_profile?: (string | null);
    min_seconds?: (number | null);
    max_seconds?: (number | null);
    supported_formats?: Array<string>;
    supports_voice?: boolean;
    supports_custom_voice?: boolean;
    supports_speed?: boolean;
    supports_emotion?: boolean;
};

