/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 某个类别当前实际生效的模型。
 */
export type EffectiveGenerationModelRead = {
    category: string;
    model_id?: (string | null);
    model_name?: (string | null);
    provider_id?: (string | null);
    provider_name?: (string | null);
    provider_key?: (string | null);
    provider_status?: (string | null);
    /**
     * project / global / missing
     */
    source?: string;
    available?: boolean;
    reason?: string;
};

