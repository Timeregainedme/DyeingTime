/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 选择式片段导出范围；shot_ids 优先，其次场次、剧集，最后 include_all。
 */
export type ClipsExportSelection = {
    /**
     * 自定义镜头 ID 列表；按数据库业务顺序重排，不按传入顺序
     */
    shot_ids?: (Array<string> | null);
    /**
     * 剧集 ID 列表
     */
    chapter_ids?: (Array<string> | null);
    /**
     * 场次 ID 列表
     */
    scene_group_ids?: (Array<string> | null);
    /**
     * 选择项目内全部镜头
     */
    include_all?: boolean;
};

