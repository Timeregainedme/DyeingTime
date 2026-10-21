/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 生成任务关联返回体。
 */
export type GenerationTaskLinkRead = {
    /**
     * 生成任务 ID
     */
    task_id: string;
    /**
     * 生成资源类型（如 image/video/text/task_link）
     */
    resource_type: string;
    /**
     * 业务类型（如 prop/costume/scene 等）
     */
    relation_type: string;
    /**
     * 关联业务实体 ID
     */
    relation_entity_id: string;
    /**
     * 关联产物文件 ID（files.id；适用于图片/音频/视频）
     */
    file_id?: (string | null);
    /**
     * 关联状态：accepted=已采用、todo=待操作、rejected=未采用
     */
    status: string;
    /**
     * 关联行 ID
     */
    id: number;
};

