/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ShotPreparationMutationAction } from './ShotPreparationMutationAction';
import type { ShotPreparationStateRead } from './ShotPreparationStateRead';
/**
 * 准备页命令执行后的统一响应。
 */
export type ShotPreparationMutationResultRead = {
    /**
     * 本次执行的准备页动作
     */
    action: ShotPreparationMutationAction;
    /**
     * 动作完成后的最新准备页聚合状态
     */
    state: ShotPreparationStateRead;
};

