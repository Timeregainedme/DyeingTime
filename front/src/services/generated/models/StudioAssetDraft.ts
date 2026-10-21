/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Studio 资产草稿（Scene/Prop/Costume）。
 *
 * 导入 API 未传 id 时由服务端生成；分镜详情回填时可带 scene_id/prop_id/costume_id。
 */
export type StudioAssetDraft = {
    /**
     * 资产 ID（已落库时回填，如 scene_id / prop_id / costume_id）
     */
    id?: (string | null);
    /**
     * 关联的文件 ID（可空）
     */
    file_id?: (string | null);
    /**
     * 缩略图下载地址（可空）
     */
    thumbnail?: (string | null);
    /**
     * 名称（同项目内建议唯一）
     */
    name: string;
    /**
     * 描述
     */
    description?: string;
    /**
     * 标签
     */
    tags?: Array<string>;
    /**
     * 提示词模板 ID（可空）
     */
    prompt_template_id?: (string | null);
    /**
     * 计划生成视角图数量
     */
    view_count?: number;
};

