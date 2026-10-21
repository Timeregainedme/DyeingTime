/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 更新生成任务关联请求体（不包含 is_adopted，采用状态由专用接口正向变更）。
 */
export type GenerationTaskLinkUpdate = {
    /**
     * 生成资源类型（如 image/video/text/task_link）
     */
    resource_type?: (string | null);
    /**
     * 业务类型（如 prop/costume/scene 等）
     */
    relation_type?: (string | null);
    /**
     * 关联业务实体 ID
     */
    relation_entity_id?: (string | null);
    /**
     * 关联产物文件 ID（files.id；适用于图片/音频/视频）
     */
    file_id?: (string | null);
    /**
     * 关联状态：accepted=已采用、todo=待操作、rejected=未采用
     */
    status?: (string | null);
};

