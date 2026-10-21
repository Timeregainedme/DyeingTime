/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 镜头对白草稿：speaker/target 使用角色 name，导入时映射为 character_id。
 */
export type StudioShotDraftDialogueLine = {
    /**
     * 镜头内排序
     */
    index?: number;
    /**
     * 台词内容
     */
    text: string;
    /**
     * 对白模式
     */
    line_mode?: 'DIALOGUE' | 'VOICE_OVER' | 'OFF_SCREEN' | 'PHONE';
    /**
     * 说话角色名称（可空）
     */
    speaker_name?: (string | null);
    /**
     * 听者角色名称（可空）
     */
    target_name?: (string | null);
};

