/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type QuotaReservationRead = {
    id: number;
    scope: string;
    media_type: string;
    amount: number;
    status: string;
    task_id?: (string | null);
    provider?: string;
    model?: string;
    note?: string;
    settled_at?: (string | null);
    created_at?: (string | null);
};

