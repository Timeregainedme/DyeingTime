/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { DashboardProjectRead } from './DashboardProjectRead';
import type { DashboardReviewRead } from './DashboardReviewRead';
import type { DashboardStatsRead } from './DashboardStatsRead';
import type { DashboardTaskRead } from './DashboardTaskRead';
/**
 * 创作工作台首页的一次性快照。
 */
export type DashboardRead = {
    /**
     * 当前工作区角色是否具备编辑权限（viewer 为 false）
     */
    can_edit: boolean;
    stats: DashboardStatsRead;
    projects?: Array<DashboardProjectRead>;
    recent_tasks?: Array<DashboardTaskRead>;
    pending_reviews?: Array<DashboardReviewRead>;
};

