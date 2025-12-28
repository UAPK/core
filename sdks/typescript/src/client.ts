/**
 * UAPK Gateway SDK Client
 */

import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios';
import type {
  ClientConfig,
  EvaluateOptions,
  ExecuteOptions,
  ExecuteWithRetryOptions,
  GatewayDecisionResponse,
  GatewayExecuteResponse,
  ApprovalStatusResponse,
  GatewayActionRequest,
} from './types';
import {
  AuthenticationError,
  ActionDeniedError,
  ActionEscalatedError,
  NetworkError,
  RateLimitError,
  ToolExecutionError,
  ValidationError,
} from './errors';

/**
 * UAPK Gateway Client
 *
 * @example
 * ```typescript
 * const client = new UAPKGatewayClient({
 *   baseURL: 'https://gateway.yourcompany.com',
 *   apiKey: 'your-api-key'
 * });
 *
 * const response = await client.execute({
 *   uapkId: 'refund-bot-v1',
 *   agentId: 'agent-123',
 *   action: {
 *     type: 'refund',
 *     tool: 'stripe_api',
 *     params: { charge_id: 'ch_123', amount: 1000 }
 *   }
 * });
 * ```
 */
export class UAPKGatewayClient {
  private readonly client: AxiosInstance;
  private readonly maxRetries: number;
  private readonly retryDelay: number;

  constructor(config: ClientConfig) {
    const { baseURL, apiKey, timeout = 30000, maxRetries = 3, retryDelay = 1000 } = config;

    this.maxRetries = maxRetries;
    this.retryDelay = retryDelay;

    this.client = axios.create({
      baseURL: baseURL.replace(/\/$/, ''),
      timeout,
      headers: {
        'X-API-Key': apiKey,
        'Content-Type': 'application/json',
        'User-Agent': 'uapk-gateway-typescript-sdk/1.0.0',
      },
    });
  }

  /**
   * Make HTTP request with retry logic and error handling
   */
  private async makeRequest<T>(
    method: 'GET' | 'POST',
    endpoint: string,
    data?: any,
    retryCount = 0
  ): Promise<T> {
    try {
      const config: AxiosRequestConfig = {
        method,
        url: endpoint,
        ...(data && { data }),
      };

      const response = await this.client.request<T>(config);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        return this.handleAxiosError(error, method, endpoint, data, retryCount);
      }
      throw new NetworkError(`Unexpected error: ${error}`);
    }
  }

  /**
   * Handle axios errors with retry logic
   */
  private async handleAxiosError<T>(
    error: AxiosError,
    method: 'GET' | 'POST',
    endpoint: string,
    data: any,
    retryCount: number
  ): Promise<T> {
    const status = error.response?.status;

    // Handle rate limiting
    if (status === 429) {
      const retryAfter = parseInt(error.response?.headers['retry-after'] || '60', 10);
      throw new RateLimitError(`Rate limit exceeded. Retry after ${retryAfter} seconds.`, retryAfter);
    }

    // Handle authentication errors
    if (status === 401) {
      throw new AuthenticationError('Invalid API key or authentication failed');
    }

    // Handle validation errors
    if (status === 422) {
      const detail = (error.response?.data as any)?.detail || 'Validation error';
      throw new ValidationError(`Request validation failed: ${detail}`);
    }

    // Handle server errors with retry
    if (status && status >= 500) {
      if (retryCount < this.maxRetries) {
        const waitTime = this.retryDelay * Math.pow(2, retryCount);
        await this.sleep(waitTime);
        return this.makeRequest<T>(method, endpoint, data, retryCount + 1);
      }
      throw new NetworkError(`Gateway server error: ${status} - ${error.message}`);
    }

    // Handle client errors
    if (status && status >= 400) {
      const detail = (error.response?.data as any)?.detail || error.message;
      throw new NetworkError(`Gateway error: ${status} - ${detail}`);
    }

    // Handle timeout and network errors with retry
    if (error.code === 'ECONNABORTED' || error.code === 'ENOTFOUND' || !error.response) {
      if (retryCount < this.maxRetries) {
        const waitTime = this.retryDelay * Math.pow(2, retryCount);
        await this.sleep(waitTime);
        return this.makeRequest<T>(method, endpoint, data, retryCount + 1);
      }
      throw new NetworkError(`Network error: ${error.message}`);
    }

    throw new NetworkError(`Request failed: ${error.message}`);
  }

  /**
   * Sleep utility for retry delays
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Evaluate an action without executing (dry-run)
   *
   * @param options - Evaluation options
   * @returns Gateway decision response
   *
   * @example
   * ```typescript
   * const decision = await client.evaluate({
   *   uapkId: 'refund-bot-v1',
   *   agentId: 'agent-123',
   *   action: {
   *     type: 'refund',
   *     tool: 'stripe_api',
   *     params: { charge_id: 'ch_123' }
   *   }
   * });
   * console.log(decision.decision); // ALLOW, DENY, or ESCALATE
   * ```
   */
  async evaluate(options: EvaluateOptions): Promise<GatewayDecisionResponse> {
    const { uapkId, agentId, action, counterparty, context, capabilityToken } = options;

    const request: GatewayActionRequest = {
      uapk_id: uapkId,
      agent_id: agentId,
      action,
      counterparty,
      context: context || {},
      capability_token: capabilityToken,
    };

    return this.makeRequest<GatewayDecisionResponse>('POST', '/api/v1/gateway/evaluate', request);
  }

  /**
   * Execute an action through the gateway
   *
   * @param options - Execution options
   * @returns Gateway execution response
   *
   * @example
   * ```typescript
   * try {
   *   const response = await client.execute({
   *     uapkId: 'refund-bot-v1',
   *     agentId: 'agent-123',
   *     action: {
   *       type: 'refund',
   *       tool: 'stripe_api',
   *       params: { charge_id: 'ch_123', amount: 1000 }
   *     }
   *   });
   *   console.log(response.result);
   * } catch (error) {
   *   if (error instanceof ActionDeniedError) {
   *     console.log('Action denied:', error.reasons);
   *   } else if (error instanceof ActionEscalatedError) {
   *     console.log('Approval required:', error.approvalId);
   *   }
   * }
   * ```
   */
  async execute(options: ExecuteOptions): Promise<GatewayExecuteResponse> {
    const {
      uapkId,
      agentId,
      action,
      counterparty,
      context,
      capabilityToken,
      overrideToken,
      raiseOnDeny = true,
      raiseOnEscalate = false,
      raiseOnToolError = true,
    } = options;

    const request: GatewayActionRequest = {
      uapk_id: uapkId,
      agent_id: agentId,
      action,
      counterparty,
      context: context || {},
      capability_token: capabilityToken,
      override_token: overrideToken,
    };

    const response = await this.makeRequest<GatewayExecuteResponse>('POST', '/api/v1/gateway/execute', request);

    // Handle DENY
    if (response.decision === 'DENY' && raiseOnDeny) {
      const reasonsStr = response.reasons.map((r) => r.message).join(', ');
      throw new ActionDeniedError(`Action denied by gateway: ${reasonsStr}`, response);
    }

    // Handle ESCALATE
    if (response.decision === 'ESCALATE' && raiseOnEscalate) {
      const reasonsStr = response.reasons.map((r) => r.message).join(', ');
      throw new ActionEscalatedError(
        `Action requires approval: ${reasonsStr} (approval_id: ${response.approval_id})`,
        response
      );
    }

    // Handle tool execution errors
    if (response.executed && response.result && !response.result.success && raiseOnToolError) {
      const errorMsg = response.result.error?.message || 'Unknown error';
      throw new ToolExecutionError(`Tool execution failed: ${errorMsg}`, response.result);
    }

    return response;
  }

  /**
   * Execute an action and wait for approval if escalated
   *
   * @param options - Execution with retry options
   * @returns Gateway execution response after approval
   *
   * @example
   * ```typescript
   * const response = await client.executeWithRetryOnEscalate({
   *   uapkId: 'refund-bot-v1',
   *   agentId: 'agent-123',
   *   action: { type: 'refund', tool: 'stripe_api', params: {...} },
   *   pollInterval: 5000,  // Check every 5 seconds
   *   maxWait: 300000      // Wait max 5 minutes
   * });
   * ```
   */
  async executeWithRetryOnEscalate(options: ExecuteWithRetryOptions): Promise<GatewayExecuteResponse> {
    const { pollInterval = 5000, maxWait = 300000, ...executeOptions } = options;

    // First attempt
    let approvalId: string;
    try {
      return await this.execute({ ...executeOptions, raiseOnEscalate: true });
    } catch (error) {
      if (error instanceof ActionEscalatedError && error.approvalId) {
        approvalId = error.approvalId;
      } else {
        throw error;
      }
    }

    // Wait for approval
    const startTime = Date.now();
    while (Date.now() - startTime < maxWait) {
      const approval = await this.getApprovalStatus(approvalId);

      if (approval.status === 'APPROVED') {
        // Retry with override token
        return this.execute({
          ...executeOptions,
          overrideToken: approval.override_token,
        });
      }

      if (approval.status === 'DENIED') {
        throw new ActionDeniedError('Approval was denied', { approval_id: approvalId });
      }

      await this.sleep(pollInterval);
    }

    throw new Error(`Approval not granted within ${maxWait}ms`);
  }

  /**
   * Get the status of an approval
   *
   * @param approvalId - Approval ID from ESCALATE response
   * @returns Approval status details
   *
   * @example
   * ```typescript
   * const approval = await client.getApprovalStatus('appr_123');
   * console.log(approval.status); // PENDING, APPROVED, or DENIED
   * ```
   */
  async getApprovalStatus(approvalId: string): Promise<ApprovalStatusResponse> {
    return this.makeRequest<ApprovalStatusResponse>('GET', `/api/v1/approvals/${approvalId}`);
  }
}
