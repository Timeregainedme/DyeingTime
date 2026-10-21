/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ShotCandidateStatus } from './ShotCandidateStatus';
/**
 * 分镜资产总览项：统一返回已关联资产与提取候选的合并视图。
 */
export type ShotAssetOverviewItem = {
    /**
     * 合并键：type:name
     */
    key: string;
    /**
     * 实体类型：character/prop/scene/costume
     */
    type: 'character' | 'prop' | 'scene' | 'costume';
    /**
     * 资产名称
     */
    name: string;
    /**
     * 候选描述（来自 extraction payload）
     */
    description?: (string | null);
    /**
     * 缩略图
     */
    thumbnail?: (string | null);
    /**
     * 缩略图或参考图文件 ID
     */
    file_id?: (string | null);
    /**
     * 来源：linked/candidate/both
     */
    source: 'linked' | 'candidate' | 'both';
    /**
     * 候选项 ID
     */
    candidate_id?: (number | null);
    /**
     * 候选确认状态
     */
    candidate_status?: (ShotCandidateStatus | null);
    /**
     * 当前已关联实体 ID
     */
    linked_entity_id?: (string | null);
    /**
     * 当前已关联实体的 image 行 ID
     */
    linked_image_id?: (number | null);
    /**
     * 当前是否已关联到镜头
     */
    is_linked: boolean;
};

