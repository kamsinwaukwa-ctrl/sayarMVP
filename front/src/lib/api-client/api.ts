/**
 * Generated API client from OpenAPI specification v0.1.1
 * Sayar WhatsApp Commerce Platform API
 */

import {
  RegisterRequest,
  AuthRequest,
  ApiResponse,
  AuthResponse,
  RegisterResponse,
  ApiClientConfiguration,
  RequestConfig,
} from './models';

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body?: any
  ) {
    super(`HTTP ${status}: ${statusText}`);
    this.name = 'ApiError';
  }
}

export class BaseAPI {
  protected configuration: ApiClientConfiguration;

  constructor(configuration: ApiClientConfiguration = {}) {
    this.configuration = {
      basePath: 'http://localhost:8000',
      ...configuration,
    };
  }

  protected async request<T>(
    path: string,
    config: RequestConfig
  ): Promise<T> {
    const url = `${this.configuration.basePath}${path}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...config.headers,
    };

    if (this.configuration.accessToken) {
      headers['Authorization'] = `Bearer ${this.configuration.accessToken}`;
    }

    const fetchConfig: RequestInit = {
      method: config.method,
      headers,
    };

    if (config.body && config.method !== 'GET') {
      fetchConfig.body = JSON.stringify(config.body);
    }

    const response = await fetch(url, fetchConfig);
    
    if (!response.ok) {
      throw new ApiError(response.status, response.statusText, await response.json());
    }

    return response.json();
  }
}

export class AuthApi extends BaseAPI {
  /**
   * Register a new user
   */
  async register(
    registerRequest: RegisterRequest,
    options?: { idempotencyKey?: string }
  ): Promise<ApiResponse<RegisterResponse>> {
    const headers: Record<string, string> = {};
    
    if (options?.idempotencyKey) {
      headers['Idempotency-Key'] = options.idempotencyKey;
    }

    return this.request<ApiResponse<RegisterResponse>>(
      '/api/v1/auth/register',
      {
        method: 'POST',
        headers,
        body: registerRequest,
      }
    );
  }

  /**
   * User login
   */
  async login(
    authRequest: AuthRequest
  ): Promise<ApiResponse<AuthResponse>> {
    return this.request<ApiResponse<AuthResponse>>(
      '/api/v1/auth/login',
      {
        method: 'POST',
        body: authRequest,
      }
    );
  }

  /**
   * Get current user information
   */
  async me(): Promise<ApiResponse<any>> {
    return this.request<ApiResponse<any>>(
      '/api/v1/auth/me',
      {
        method: 'GET',
      }
    );
  }
}

export class Configuration {
  constructor(private config: ApiClientConfiguration = {}) {}
  
  get basePath(): string {
    return this.config.basePath || 'http://localhost:8000';
  }
  
  get accessToken(): string | undefined {
    return this.config.accessToken;
  }
}

// Export everything
export * from './models';
export default AuthApi;