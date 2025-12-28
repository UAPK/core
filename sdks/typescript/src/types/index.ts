/**
 * TypeScript types and interfaces for UAPK Gateway SDK
 */

import { z } from 'zod';

/**
 * Gateway decision types
 */
export enum GatewayDecision {
  ALLOW = 'ALLOW',
  DENY = 'DENY',
  ESCALATE = 'ESCALATE',
}

/**
 * Reason codes for gateway decisions
 */
export enum ReasonCode {
  MANIFEST_NOT_FOUND = 'MANIFEST_NOT_FOUND',
  MANIFEST_INACTIVE = 'MANIFEST_INACTIVE',
  ACTION_TYPE_DENIED = 'ACTION_TYPE_DENIED',
  TOOL_NOT_ALLOWED = 'TOOL_NOT_ALLOWED',
  BUDGET_EXCEEDED = 'BUDGET_EXCEEDED',
  AMOUNT_CAP_EXCEEDED = 'AMOUNT_CAP_EXCEEDED',
  JURISDICTION_DENIED = 'JURISDICTION_DENIED',
  COUNTERPARTY_DENIED = 'COUNTERPARTY_DENIED',
  APPROVAL_REQUIRED = 'APPROVAL_REQUIRED',
  CAPABILITY_TOKEN_INVALID = 'CAPABILITY_TOKEN_INVALID',
  CAPABILITY_TOKEN_EXPIRED = 'CAPABILITY_TOKEN_EXPIRED',
  OVERRIDE_TOKEN_ALREADY_USED = 'OVERRIDE_TOKEN_ALREADY_USED',
  POLICY_ALLOWS = 'POLICY_ALLOWS',
}

/**
 * Action information schema and type
 */
export const ActionInfoSchema = z.object({
  type: z.string().describe('Action type (e.g., "refund", "send_email")'),
  tool: z.string().describe('Tool/connector to execute'),
  params: z.record(z.any()).describe('Tool parameters'),
  amount: z.number().optional().describe('Transaction amount (if applicable)'),
  currency: z.string().optional().describe('Currency code (if applicable)'),
  description: z.string().optional().describe('Human-readable description'),
});

export type ActionInfo = z.infer<typeof ActionInfoSchema>;

/**
 * Counterparty information schema and type
 */
export const CounterpartyInfoSchema = z.object({
  id: z.string().optional().describe('Counterparty identifier'),
  name: z.string().optional().describe('Counterparty name'),
  email: z.string().email().optional().describe('Email address'),
  domain: z.string().optional().describe('Domain name'),
  jurisdiction: z.string().optional().describe('Jurisdiction/country code'),
});

export type CounterpartyInfo = z.infer<typeof CounterpartyInfoSchema>;

/**
 * Reason detail schema and type
 */
export const ReasonDetailSchema = z.object({
  code: z.nativeEnum(ReasonCode),
  message: z.string(),
  details: z.record(z.any()).optional(),
});

export type ReasonDetail = z.infer<typeof ReasonDetailSchema>;

/**
 * Gateway action request schema and type
 */
export const GatewayActionRequestSchema = z.object({
  uapk_id: z.string().describe('UAPK manifest ID'),
  agent_id: z.string().describe('Agent instance identifier'),
  action: ActionInfoSchema,
  counterparty: CounterpartyInfoSchema.optional(),
  context: z.record(z.any()).optional().default({}),
  capability_token: z.string().optional().describe('Capability token (if delegated)'),
  override_token: z.string().optional().describe('Override token from approval'),
});

export type GatewayActionRequest = z.infer<typeof GatewayActionRequestSchema>;

/**
 * Gateway decision response schema and type
 */
export const GatewayDecisionResponseSchema = z.object({
  interaction_id: z.string(),
  decision: z.nativeEnum(GatewayDecision),
  reasons: z.array(ReasonDetailSchema),
  approval_id: z.string().optional(),
  timestamp: z.string().datetime(),
  policy_version: z.string(),
});

export type GatewayDecisionResponse = z.infer<typeof GatewayDecisionResponseSchema>;

/**
 * Tool result schema and type
 */
export const ToolResultSchema = z.object({
  success: z.boolean(),
  data: z.record(z.any()).optional(),
  error: z.record(z.any()).optional(),
  result_hash: z.string().optional(),
  duration_ms: z.number().optional(),
});

export type ToolResult = z.infer<typeof ToolResultSchema>;

/**
 * Gateway execute response schema and type
 */
export const GatewayExecuteResponseSchema = GatewayDecisionResponseSchema.extend({
  executed: z.boolean(),
  result: ToolResultSchema.optional(),
});

export type GatewayExecuteResponse = z.infer<typeof GatewayExecuteResponseSchema>;

/**
 * Approval status response
 */
export interface ApprovalStatusResponse {
  id: string;
  status: 'PENDING' | 'APPROVED' | 'DENIED';
  created_at: string;
  updated_at: string;
  override_token?: string;
}

/**
 * Client configuration options
 */
export interface ClientConfig {
  baseURL: string;
  apiKey: string;
  timeout?: number;
  maxRetries?: number;
  retryDelay?: number;
}

/**
 * Execute options
 */
export interface ExecuteOptions {
  uapkId: string;
  agentId: string;
  action: ActionInfo;
  counterparty?: CounterpartyInfo;
  context?: Record<string, any>;
  capabilityToken?: string;
  overrideToken?: string;
  raiseOnDeny?: boolean;
  raiseOnEscalate?: boolean;
  raiseOnToolError?: boolean;
}

/**
 * Evaluate options
 */
export interface EvaluateOptions {
  uapkId: string;
  agentId: string;
  action: ActionInfo;
  counterparty?: CounterpartyInfo;
  context?: Record<string, any>;
  capabilityToken?: string;
}

/**
 * Execute with retry options
 */
export interface ExecuteWithRetryOptions extends ExecuteOptions {
  pollInterval?: number;
  maxWait?: number;
}
