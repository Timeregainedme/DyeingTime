/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 剧本分镜请求。
 */
export type ScriptDividerRequest = {
    /**
     * 完整剧本文本
     */
    script_text: string;
    /**
     * 是否将分镜写入数据库（AI Studio shots 表）
     */
    write_to_db?: boolean;
    /**
     * 章节 ID（write_to_db=true 时必填）
     */
    chapter_id?: (string | null);
};

