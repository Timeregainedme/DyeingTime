/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ShotSemanticSuggestion } from './ShotSemanticSuggestion';
import type { StudioShotDraftDialogueLine } from './StudioShotDraftDialogueLine';
/**
 * 镜头草稿：不含 shot_id，由导入 API 生成；引用实体用 name。
 */
export type StudioShotDraft = {
    /**
     * 镜头序号（章节内唯一）
     */
    index: number;
    /**
     * 镜头标题
     */
    title: string;
    /**
     * 剧本摘录
     */
    script_excerpt?: string;
    /**
     * 场景名称（可选）
     */
    scene_name?: (string | null);
    /**
     * 本镜出现角色名称列表
     */
    character_names?: Array<string>;
    /**
     * 本镜关键道具名称列表
     */
    prop_names?: Array<string>;
    /**
     * 本镜服装名称列表
     */
    costume_names?: Array<string>;
    /**
     * 对白列表
     */
    dialogue_lines?: Array<StudioShotDraftDialogueLine>;
    /**
     * 动作/场景描述
     */
    actions?: Array<string>;
    /**
     * 镜头语言默认建议与动作拍点候选
     */
    semantic_suggestion?: (ShotSemanticSuggestion | null);
};

