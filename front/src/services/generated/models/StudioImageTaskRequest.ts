/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Studio 专用图片任务请求体：可选模型 ID，不传则用默认图片模型；供应商由模型反查。
 *
 * image_id 表示具体的图片模型 ID，例如：
 * - 演员图片：ActorImage.id
 * - 场景图片：SceneImage.id
 * - 道具图片：PropImage.id
 * - 服装图片：CostumeImage.id
 * - 角色图片：CharacterImage.id
 * - 分镜帧图片：ShotFrameImage.id
 */
export type StudioImageTaskRequest = {
    /**
     * 可选模型 ID（models.id）；不传则使用 ModelSettings.default_image_model_id；Provider 由模型关联反查
     */
    model_id?: (string | null);
    /**
     * 图片模型 ID，如 ActorImage.id / SceneImage.id / PropImage.id 等；必须与路径主体 ID 匹配
     */
    image_id?: (number | null);
    /**
     * 提示词（由前端传入）。创建任务接口必填；render-prompt 接口可不传
     */
    prompt?: (string | null);
    /**
     * 参考图 file_id 列表（可多张，顺序有效）。创建任务接口会基于 file_id 从数据中解析为参考图
     */
    images?: Array<string>;
};

