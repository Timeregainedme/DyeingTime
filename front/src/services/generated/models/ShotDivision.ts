/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 剧本分镜中的单镜信息：行号 + 预览文本（可选弱语义）。
 */
export type ShotDivision = {
    /**
     * 镜头序号（章节内唯一）
     */
    index: number;
    /**
     * 起始行号（1-based）
     */
    start_line: number;
    /**
     * 结束行号（1-based）
     */
    end_line: number;
    /**
     * 镜头对应的剧本摘录/文本
     */
    script_excerpt: string;
    /**
     * 镜头名称（分镜名/镜头标题）
     */
    shot_name?: string;
    /**
     * 时间（日/夜/未知等，可选）
     */
    time_of_day?: ('DAY' | 'NIGHT' | 'DAWN' | 'DUSK' | 'UNKNOWN' | '日' | '夜' | '黎明' | '黄昏' | '不明' | '未知' | null);
};

