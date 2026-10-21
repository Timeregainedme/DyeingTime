/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ShotAssetOverviewItem } from './ShotAssetOverviewItem';
import type { ShotAssetsOverviewSummary } from './ShotAssetsOverviewSummary';
import type { ShotStatus } from './ShotStatus';
export type ShotAssetsOverviewRead = {
    /**
     * 镜头 ID
     */
    shot_id: string;
    /**
     * 是否明确跳过提取
     */
    skip_extraction: boolean;
    /**
     * 镜头流程状态
     */
    status: ShotStatus;
    /**
     * 总览统计
     */
    summary: ShotAssetsOverviewSummary;
    /**
     * 资产总览项
     */
    items?: Array<ShotAssetOverviewItem>;
};

