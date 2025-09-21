/**
 * API Client for Sayar WhatsApp Commerce Platform
 * Integrates with FastAPI backend using generated TypeScript client
 */

import { 
  AuthRequest, 
  RegisterRequest, 
  AuthResponse, 
  RegisterResponse,
} from '@/types/api'

export class ApiClientError extends Error {
  public code: string
  public status: number
  public details?: any
  public requestId?: string

  constructor(message: string, code: string, status: number, details?: any, requestId?: string) {
    super(message)
    this.name = 'ApiClientError'
    this.code = code
    this.status = status
    this.details = details
    this.requestId = requestId
  }
}

export class ApiClient {
  private baseUrl: string
  private token: string | null = null

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/$/, '') // Remove trailing slash
    
    // Try to get token from localStorage on initialization
    this.token = this.getStoredToken()
  }

  private getStoredToken(): string | null {
    try {
      return localStorage.getItem('access_token')
    } catch {
      return null
    }
  }

  private setStoredToken(token: string | null): void {
    try {
      if (token) {
        localStorage.setItem('access_token', token)
      } else {
        localStorage.removeItem('access_token')
      }
      this.token = token
    } catch (error) {
      console.warn('Failed to store auth token:', error)
    }
  }

  public setAuthToken(token: string | null): void {
    this.setStoredToken(token)
  }

  public getAuthToken(): string | null {
    return this.token
  }

  public isAuthenticated(): boolean {
    return !!this.token
  }

  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    }

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`
    }

    return headers
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    let data: any

    try {
      data = await response.json()
    } catch (error) {
      throw new ApiClientError(
        'Invalid response format',
        'INVALID_RESPONSE',
        response.status
      )
    }

    // Handle successful responses
    if (response.ok && data.ok) {
      return data.data || data
    }

    // Handle error responses
    if (!response.ok || !data.ok) {
      // Handle FastAPI error response format - prioritize user-friendly messages for auth errors
      const errorMessage = 
        (response.status === 401 && data.error?.code === 'AUTHENTICATION_ERROR') 
          ? 'Invalid credentials. Please check your email and password.'
          : data.error?.message || 
            data.detail || 
            data.message || 
            `HTTP ${response.status}: ${response.statusText}`
      
      const errorCode = data.error?.code || data.code || 'API_ERROR'
      
      throw new ApiClientError(
        errorMessage,
        errorCode,
        response.status,
        data.error?.details || data.details || data.detail,
        data.error?.request_id || data.request_id
      )
    }

    return data
  }

  private async request<T>(
    method: string,
    endpoint: string,
    body?: any,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    
    const config: RequestInit = {
      method,
      headers: {
        ...this.getHeaders(),
        ...options.headers,
      },
      ...options,
    }

    if (body) {
      config.body = JSON.stringify(body)
    }

    try {
      const response = await fetch(url, config)
      return this.handleResponse<T>(response)
    } catch (error) {
      if (error instanceof ApiClientError) {
        throw error
      }
      
      // Network or other fetch errors
      throw new ApiClientError(
        error instanceof Error ? error.message : 'Network error',
        'NETWORK_ERROR',
        0
      )
    }
  }

  // Auth endpoints
  public async login(credentials: AuthRequest): Promise<AuthResponse> {
    const response = await this.request<AuthResponse>(
      'POST',
      '/api/v1/auth/login',
      credentials
    )
    
    // Store token automatically after successful login
    if (response.token) {
      this.setAuthToken(response.token)
    }
    
    return response
  }

  public async register(userData: RegisterRequest): Promise<RegisterResponse> {
    const response = await this.request<RegisterResponse>(
      'POST',
      '/api/v1/auth/register',
      userData
    )
    
    // Store token automatically after successful registration
    if (response.token) {
      this.setAuthToken(response.token)
    }
    
    return response
  }

  public async getCurrentUser(): Promise<AuthResponse['user']> {
    return this.request<AuthResponse['user']>('GET', '/api/v1/auth/me')
  }

  public async logout(): Promise<void> {
    // Clear stored token
    this.setAuthToken(null)
    
    // Optionally call backend logout endpoint if it exists
    try {
      await this.request('POST', '/api/v1/auth/logout')
    } catch (error) {
      // Ignore logout endpoint errors - token is already cleared
      console.warn('Logout endpoint error (ignored):', error)
    }
  }

  // Merchant endpoints
  public async getCurrentMerchant(): Promise<any> {
    return this.request('GET', '/api/v1/merchants/me')
  }

  // Products endpoints
  public async getProducts(params?: any): Promise<any> {
    const query = params ? `?${new URLSearchParams(params).toString()}` : ''
    return this.request('GET', `/api/v1/products${query}`)
  }

  // Health check
  public async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return this.request('GET', '/healthz')
  }

  // Generic HTTP methods for inheritance
  protected async get<T>(endpoint: string, options?: RequestInit): Promise<T> {
    return this.request<T>('GET', endpoint, undefined, options)
  }

  protected async post<T>(endpoint: string, body?: any, options?: RequestInit): Promise<T> {
    return this.request<T>('POST', endpoint, body, options)
  }

  protected async put<T>(endpoint: string, body?: any, options?: RequestInit): Promise<T> {
    return this.request<T>('PUT', endpoint, body, options)
  }

  protected async patch<T>(endpoint: string, body?: any, options?: RequestInit): Promise<T> {
    return this.request<T>('PATCH', endpoint, body, options)
  }

  protected async delete<T>(endpoint: string, options?: RequestInit): Promise<T> {
    return this.request<T>('DELETE', endpoint, undefined, options)
  }
}

// Create and export singleton instance
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
export const apiClient = new ApiClient(apiBaseUrl)

// Export default for backwards compatibility
export default apiClient