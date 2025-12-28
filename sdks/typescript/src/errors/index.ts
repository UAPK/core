/**
 * Error classes for UAPK Gateway SDK
 */

import type { GatewayDecisionResponse, GatewayExecuteResponse, ReasonDetail, ToolResult } from '../types';

/**
 * Base error class for all UAPK Gateway SDK errors
 */
export class UAPKGatewayError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'UAPKGatewayError';
    Object.setPrototypeOf(this, UAPKGatewayError.prototype);
  }
}

/**
 * Thrown when API key authentication fails
 */
export class AuthenticationError extends UAPKGatewayError {
  constructor(message: string) {
    super(message);
    this.name = 'AuthenticationError';
    Object.setPrototypeOf(this, AuthenticationError.prototype);
  }
}

/**
 * Thrown when an action is denied by the gateway
 */
export class ActionDeniedError extends UAPKGatewayError {
  public readonly decisionResponse: Partial<GatewayDecisionResponse | GatewayExecuteResponse>;
  public readonly reasons: ReasonDetail[];
  public readonly interactionId?: string;

  constructor(message: string, decisionResponse: Partial<GatewayDecisionResponse | GatewayExecuteResponse>) {
    super(message);
    this.name = 'ActionDeniedError';
    this.decisionResponse = decisionResponse;
    this.reasons = decisionResponse.reasons || [];
    this.interactionId = decisionResponse.interaction_id;
    Object.setPrototypeOf(this, ActionDeniedError.prototype);
  }
}

/**
 * Thrown when an action requires approval
 */
export class ActionEscalatedError extends UAPKGatewayError {
  public readonly decisionResponse: Partial<GatewayDecisionResponse | GatewayExecuteResponse>;
  public readonly approvalId?: string;
  public readonly interactionId?: string;
  public readonly reasons: ReasonDetail[];

  constructor(message: string, decisionResponse: Partial<GatewayDecisionResponse | GatewayExecuteResponse>) {
    super(message);
    this.name = 'ActionEscalatedError';
    this.decisionResponse = decisionResponse;
    this.approvalId = decisionResponse.approval_id;
    this.interactionId = decisionResponse.interaction_id;
    this.reasons = decisionResponse.reasons || [];
    Object.setPrototypeOf(this, ActionEscalatedError.prototype);
  }
}

/**
 * Thrown when tool execution fails
 */
export class ToolExecutionError extends UAPKGatewayError {
  public readonly toolResult: Partial<ToolResult>;
  public readonly error: Record<string, any>;

  constructor(message: string, toolResult: Partial<ToolResult>) {
    super(message);
    this.name = 'ToolExecutionError';
    this.toolResult = toolResult;
    this.error = toolResult.error || {};
    Object.setPrototypeOf(this, ToolExecutionError.prototype);
  }
}

/**
 * Thrown when network or HTTP errors occur
 */
export class NetworkError extends UAPKGatewayError {
  constructor(message: string) {
    super(message);
    this.name = 'NetworkError';
    Object.setPrototypeOf(this, NetworkError.prototype);
  }
}

/**
 * Thrown when request validation fails
 */
export class ValidationError extends UAPKGatewayError {
  constructor(message: string) {
    super(message);
    this.name = 'ValidationError';
    Object.setPrototypeOf(this, ValidationError.prototype);
  }
}

/**
 * Thrown when rate limit is exceeded
 */
export class RateLimitError extends UAPKGatewayError {
  public readonly retryAfter?: number;

  constructor(message: string, retryAfter?: number) {
    super(message);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
    Object.setPrototypeOf(this, RateLimitError.prototype);
  }
}
