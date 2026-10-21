/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ShotExtractionSummaryRead = {
    /**
     * 镜头提取确认状态摘要
     */
    state: 'not_extracted' | 'extracted_empty' | 'extracted_pending' | 'extracted_resolved' | 'skipped';
    /**
     * 是否已执行过提取
     */
    has_extracted: boolean;
    /**
     * 最近一次提取完成时间
     */
    last_extracted_at?: (string | null);
    /**
     * 资产候选总数
     */
    asset_candidate_total?: number;
    /**
     * 对白候选总数
     */
    dialogue_candidate_total?: number;
    /**
     * 待确认资产候选数
     */
    pending_asset_count?: number;
    /**
     * 待确认对白候选数
     */
    pending_dialogue_count?: number;
};

