/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 最近生成任务概览。只暴露任务中心已有的通用字段。
 */
export type DashboardTaskRead = {
    id: string;
    task_kind: string;
    status: string;
    progress: number;
    created_at?: (string | null);
    updated_at?: (string | null);
    project_id?: (string | null);
    project_name?: (string | null);
};

