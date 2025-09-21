const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

class ApiClient {
  private baseURL: string

  constructor(baseURL: string) {
    this.baseURL = baseURL
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    
    // Handle headers properly for FormData vs JSON
    const isFormData = options.body instanceof FormData
    const headers: Record<string, string> = {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...(options.headers as Record<string, string>),
    }

    // Add authentication token if available
    const token = localStorage.getItem('access_token')
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }
    
    const config: RequestInit = {
      ...options,
      headers,
    }

    const response = await fetch(url, config)

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return response.json()
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' })
  }

  async post<T>(endpoint: string, data: Record<string, unknown> | FormData): Promise<T> {
    const body = data instanceof FormData ? data : JSON.stringify(data)
    return this.request<T>(endpoint, {
      method: 'POST',
      body,
    })
  }

  async put<T>(endpoint: string, data: Record<string, unknown> | FormData): Promise<T> {
    const body = data instanceof FormData ? data : JSON.stringify(data)
    return this.request<T>(endpoint, {
      method: 'PUT',
      body,
    })
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' })
  }
}

export const api = new ApiClient(API_BASE_URL)