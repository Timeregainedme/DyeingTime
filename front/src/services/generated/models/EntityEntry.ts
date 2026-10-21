/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EntityVariant } from './EntityVariant';
import type { EvidenceSpan } from './EvidenceSpan';
/**
 * 合并后的实体条目（脚本处理中间态）。
 */
export type EntityEntry = {
    /**
     * 实体稳定ID（合并阶段分配）
     */
    id: string;
    /**
     * 实体名称
     */
    name: string;
    /**
     * 实体类型
     */
    type: 'character' | 'scene' | 'prop' | 'location';
    /**
     * 归一化名称（来自文本，可选）
     */
    normalized_name?: (string | null);
    /**
     * 别名/称呼（来自文本，可选）
     */
    aliases?: Array<string>;
    /**
     * 基础画像/描述（忠实文本，简短）
     */
    description?: (string | null);
    /**
     * 合并确定度 0-1（可选）
     */
    confidence?: (number | null);
    /**
     * 首次出场证据（可选）
     */
    first_appearance?: (EvidenceSpan | null);
    /**
     * 服装/造型描述（可选，便于变体与资产关联）
     */
    costume_note?: (string | null);
    /**
     * 性格/特征词（可选）
     */
    traits?: Array<string>;
    /**
     * 地点类型：房间/街道/森林/车厢等（可选）
     */
    location_type?: (string | null);
    /**
     * 道具类别（可选：weapon/document/vehicle/clothing/device/magic_item/other）
     */
    category?: (string | null);
    /**
     * 拥有者角色ID（可选）
     */
    owner_character_id?: (string | null);
    /**
     * 支撑该实体画像的证据片段（可选）
     */
    evidence?: Array<EvidenceSpan>;
    /**
     * 首次出现的镜头序号
     */
    first_shot?: (number | null);
    /**
     * 出现镜头列表
     */
    appearances?: Array<number>;
    /**
     * 变体列表
     */
    variants?: Array<EntityVariant>;
};

