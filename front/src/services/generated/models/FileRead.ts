/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { FileTypeEnum } from './FileTypeEnum';
export type FileRead = {
    /**
     * 文件 ID
     */
    id: string;
    /**
     * 文件类型
     */
    type: FileTypeEnum;
    /**
     * 文件名/标题
     */
    name: string;
    /**
     * 缩略图 URL/路径
     */
    thumbnail?: string;
    /**
     * 标签
     */
    tags?: Array<string>;
};

