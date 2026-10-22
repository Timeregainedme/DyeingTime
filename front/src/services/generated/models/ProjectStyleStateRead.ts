/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ProjectStyleOptionRead } from './ProjectStyleOptionRead';
import type { ProjectStyleSnapshotRead } from './ProjectStyleSnapshotRead';
/**
 * 项目风格面板的完整状态。
 */
export type ProjectStyleStateRead = {
    project_id: string;
    locked: boolean;
    style?: (ProjectStyleOptionRead | null);
    snapshot?: (ProjectStyleSnapshotRead | null);
    styles?: Array<ProjectStyleOptionRead>;
    visual_styles?: Array<string>;
};

