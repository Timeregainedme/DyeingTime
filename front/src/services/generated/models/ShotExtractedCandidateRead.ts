/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ShotCandidateStatus } from './ShotCandidateStatus';
import type { ShotCandidateType } from './ShotCandidateType';
export type ShotExtractedCandidateRead = {
    /**
     * 候选项 ID
     */
    id: number;
    /**
     * 所属镜头 ID
     */
    shot_id: string;
    /**
     * 候选类型
     */
    candidate_type: ShotCandidateType;
    /**
     * 提取出的候选名称
     */
    candidate_name: string;
    /**
     * 候选确认状态
     */
    candidate_status: ShotCandidateStatus;
    /**
     * 已关联实体 ID
     */
    linked_entity_id?: (string | null);
    /**
     * 候选来源
     */
    source: string;
    /**
     * 候选附加信息
     */
    payload?: Record<string, any>;
    /**
     * 确认时间
     */
    confirmed_at?: (string | null);
    /**
     * 创建时间
     */
    created_at: string;
    /**
     * 更新时间
     */
    updated_at: string;
};

