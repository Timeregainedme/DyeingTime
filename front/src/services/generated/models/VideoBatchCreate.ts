/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type VideoBatchCreate = {
    shot_ids: Array<string>;
    candidate_count?: number;
    concurrency?: (number | null);
    scene_group_id?: (string | null);
    /**
     * 分镜覆盖率低时需显式确认
     */
    allow_low_coverage?: boolean;
    /**
     * 客户端幂等键；同一剧集内相同 key 只创建一个批次
     */
    request_key?: (string | null);
};

