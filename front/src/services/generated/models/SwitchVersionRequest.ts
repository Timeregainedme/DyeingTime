/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type SwitchVersionRequest = {
    version_id: string;
    /**
     * 角色身份并发检查；不匹配返回 409
     */
    expected_lock_version?: (number | null);
};

