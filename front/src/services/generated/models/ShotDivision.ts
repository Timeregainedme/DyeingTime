/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 剧本分镜中的单镜信息。
 *
 * 快速切分只依赖 `index` / `script_excerpt` / `shot_name`；行号与时间字段是历史
 * 可选信息，不再作为写入数据库的硬前置，避免模型输出近义词导致整单校验失败。
 */
export type ShotDivision = {
    /**
     * 镜头序号（章节内唯一）
     */
    index: number;
    /**
     * 起始行号（1-based，可选）
     */
    start_line?: (number | null);
    /**
     * 结束行号（1-based，可选）
     */
    end_line?: (number | null);
    /**
     * 镜头对应的剧本摘录/文本
     */
    script_excerpt: string;
    /**
     * 镜头名称（分镜名/镜头标题）
     */
    shot_name?: string;
    /**
     * 时间描述（自由文本，可选；不再参与强校验）
     */
    time_of_day?: (string | null);
};

