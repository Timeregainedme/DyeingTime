/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TaskStatus } from './TaskStatus';
export type TaskCancelRead = {
    task_id: string;
    status: TaskStatus;
    /**
     * 是否已登记取消请求
     */
    cancel_requested: boolean;
    /**
     * 请求取消时间戳
     */
    cancel_requested_at_ts?: (number | null);
    /**
     * 是否已立即取消完成
     */
    effective_immediately?: boolean;
};

