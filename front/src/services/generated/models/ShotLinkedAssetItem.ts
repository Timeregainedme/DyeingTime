/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 按分镜聚合返回的关联资产条目（角色/道具/场景/服装）。
 */
export type ShotLinkedAssetItem = {
    /**
     * 实体类型：character/prop/scene/costume
     */
    type: 'character' | 'prop' | 'scene' | 'costume';
    /**
     * 实体 ID（如 character_id/prop_id/scene_id/costume_id）
     */
    id: string;
    /**
     * 最佳缩略图对应的 image 行 ID（如 PropImage.id）；无图则为 null
     */
    image_id?: (number | null);
    /**
     * 最佳缩略图对应的文件 ID（files.id）；用于参考图输入；无图则为 null
     */
    file_id?: (string | null);
    /**
     * 实体名称
     */
    name: string;
    /**
     * 缩略图下载地址（/api/v1/studio/files/{file_id}/download）
     */
    thumbnail?: string;
};

