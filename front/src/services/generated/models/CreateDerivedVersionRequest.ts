/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type CreateDerivedVersionRequest = {
    name: string;
    description?: string;
    variant_type?: 'base' | 'costume' | 'hairstyle' | 'makeup' | 'age' | 'weather' | 'lighting' | 'other';
    parent_version_id?: (string | null);
    costume_id?: (string | null);
    attributes?: Record<string, any>;
    activate?: boolean;
};

