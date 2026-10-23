/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 用于视频提示词的结构化台词行（保留对白模式、说话人和声音描述）。
 */
export type ShotPromptDialogueRead = {
    /**
     * 镜头内行号
     */
    index?: number;
    /**
     * 结构化说话角色 ID
     */
    speaker_character_id?: (string | null);
    /**
     * 说话人名称
     */
    speaker_name?: string;
    /**
     * 台词文本
     */
    text?: string;
    /**
     * 情绪/语气
     */
    emotion?: (string | null);
    /**
     * 对白模式：DIALOGUE/VOICE_OVER/OFF_SCREEN/PHONE
     */
    line_mode?: string;
    /**
     * 角色声音描述，仅使用用户配置，不按姓名推断
     */
    voice_description?: string;
    /**
     * 已生成配音的文件 ID
     */
    generated_audio_file_id?: (string | null);
};

