/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type P6VideoGenerateRequest = {
    /**
     * 自然语言 @ 引用提示词
     */
    prompt?: string;
    /**
     * 高级最终 H3 提示词；非空时优先
     */
    advanced_prompt?: string;
    reference_mode?: 'reference' | 'text_only';
    ratio?: (string | null);
    resolution?: (string | null);
    reference_audio_file_ids?: Array<string>;
    /**
     * 预览返回的 input_hash；提交时不一致则拒绝，要求刷新预览
     */
    expected_input_hash?: (string | null);
    /**
     * 生成完成后是否自动采纳；P6 默认显式采纳
     */
    auto_adopt?: boolean;
    /**
     * 客户端幂等键；相同 key + 相同输入返回已有任务
     */
    request_key?: (string | null);
};

