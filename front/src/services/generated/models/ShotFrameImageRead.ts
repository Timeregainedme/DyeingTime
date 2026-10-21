/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ShotFrameType } from './ShotFrameType';
export type ShotFrameImageRead = {
    /**
     * 图片行 ID
     */
    id: number;
    /**
     * 所属镜头细节 ID
     */
    shot_detail_id: string;
    /**
     * 帧类型：first/last/key
     */
    frame_type: ShotFrameType;
    /**
     * 关联的 FileItem ID（可为空，允许先创建占位）
     */
    file_id?: (string | null);
    /**
     * 宽(px)
     */
    width?: (number | null);
    /**
     * 高(px)
     */
    height?: (number | null);
    /**
     * 格式
     */
    format?: string;
};

