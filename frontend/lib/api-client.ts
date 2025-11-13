/**
 * API Client for Praxis Labs Backend
 * Handles authentication, requests, and error handling
 */

import axios, { AxiosError, AxiosInstance } from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000, // 30 seconds
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    // Get token from localStorage
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Handle 401 Unauthorized - token expired or invalid
    if (error.response?.status === 401) {
      // Clear token and redirect to login
      if (typeof window !== "undefined") {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
        window.location.href = "/auth/login";
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;

// Type definitions
export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  email: string;
  full_name: string | null;
}

export interface User {
  user_id: string;
  email: string;
  full_name: string | null;
  email_verified: boolean;
  is_active: boolean;
  created_at: string;
}

export interface APIKey {
  key_id: string;
  key_name: string | null;
  key_prefix: string;
  scopes: string[];
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
  is_active: boolean;
  api_key?: string; // Only present when creating a new key
}

export interface UsageDataPoint {
  timestamp: string;
  count: number;
  success_count: number;
  error_count: number;
  avg_latency_ms: number | null;
}

export interface UsageAnalytics {
  total_requests: number;
  success_rate: number;
  avg_latency_ms: number;
  data_points: UsageDataPoint[];
}

export interface SafetyIncident {
  incident_id: number;
  timestamp: string;
  severity: string;
  violation_type: string;
  robot_type: string;
  environment_type: string;
  action_taken: string;
}

export interface SafetyAnalytics {
  total_incidents: number;
  critical_incidents: number;
  high_severity_incidents: number;
  incidents_by_type: Record<string, number>;
  recent_incidents: SafetyIncident[];
}

export interface RobotProfile {
  robot_type: string;
  total_inferences: number;
  success_rate: number;
  avg_latency_ms: number;
  avg_safety_score: number;
  common_instructions: string[];
}

export interface Subscription {
  subscription_id: string | null;
  status: string | null;
  tier: string;
  monthly_quota: number | null;
  monthly_usage: number;
  cancel_at_period_end: boolean | null;
}

// API Methods
export const api = {
  // Authentication
  async register(email: string, password: string, full_name?: string, company_name?: string): Promise<LoginResponse> {
    const { data } = await apiClient.post<LoginResponse>("/auth/register", {
      email,
      password,
      full_name,
      company_name,
    });
    return data;
  },

  async login(email: string, password: string): Promise<LoginResponse> {
    // OAuth2 password flow uses form data
    const formData = new FormData();
    formData.append("username", email); // OAuth2 uses "username" field
    formData.append("password", password);

    const { data } = await apiClient.post<LoginResponse>("/auth/login", formData, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });
    return data;
  },

  async logout(): Promise<void> {
    await apiClient.post("/auth/logout");
  },

  async getMe(): Promise<User> {
    const { data } = await apiClient.get<User>("/auth/me");
    return data;
  },

  async forgotPassword(email: string): Promise<void> {
    await apiClient.post("/auth/forgot-password", { email });
  },

  async resetPassword(token: string, new_password: string): Promise<void> {
    await apiClient.post("/auth/reset-password", { token, new_password });
  },

  // API Keys
  async getAPIKeys(): Promise<APIKey[]> {
    const { data } = await apiClient.get<APIKey[]>("/v1/api-keys");
    return data;
  },

  async createAPIKey(key_name: string, scopes: string[], expires_in_days?: number): Promise<APIKey> {
    const { data } = await apiClient.post<APIKey>("/v1/api-keys", {
      key_name,
      scopes,
      expires_in_days,
    });
    return data;
  },

  async revokeAPIKey(key_id: string): Promise<void> {
    await apiClient.delete(`/v1/api-keys/${key_id}`);
  },

  // Analytics
  async getUsageAnalytics(days: number = 30): Promise<UsageAnalytics> {
    const { data } = await apiClient.get<UsageAnalytics>(`/v1/analytics/usage?days=${days}`);
    return data;
  },

  async getSafetyAnalytics(days: number = 30): Promise<SafetyAnalytics> {
    const { data } = await apiClient.get<SafetyAnalytics>(`/v1/analytics/safety?days=${days}`);
    return data;
  },

  async getRobotProfiles(days: number = 30): Promise<RobotProfile[]> {
    const { data } = await apiClient.get<{ profiles: RobotProfile[] }>(`/v1/analytics/robot-profiles?days=${days}`);
    return data.profiles;
  },

  // Billing
  async getSubscription(): Promise<Subscription> {
    const { data } = await apiClient.get<Subscription>("/v1/billing/subscription");
    return data;
  },

  async createCheckoutSession(tier: string, success_url: string, cancel_url: string) {
    const { data } = await apiClient.post("/v1/billing/checkout", {
      tier,
      success_url,
      cancel_url,
    });
    return data;
  },

  async getBillingPortal(return_url: string) {
    const { data } = await apiClient.get("/v1/billing/portal", {
      params: { return_url },
    });
    return data;
  },

  // Inference (for playground)
  async runInference(image: string, instruction: string, robot_type?: string) {
    const { data } = await apiClient.post("/v1/inference", {
      image,
      instruction,
      robot_type: robot_type || "franka_panda",
    });
    return data;
  },

  // Inference History
  async getInferenceHistory(page: number = 1, limit: number = 20, filters?: {
    status?: string;
    robot_type?: string;
    start_date?: string;
    end_date?: string;
  }) {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
      ...filters,
    });
    const { data } = await apiClient.get(`/v1/inference/history?${params}`);
    return data;
  },

  async getTopInstructions(days: number = 30, limit: number = 10) {
    const { data } = await apiClient.get(`/v1/analytics/top-instructions?days=${days}&limit=${limit}`);
    return data;
  },

  // User Profile
  async updateUserProfile(updates: { full_name?: string; company_name?: string }) {
    const { data } = await apiClient.patch("/users/me/profile", updates);
    return data;
  },

  async changePassword(current_password: string, new_password: string) {
    await apiClient.post("/users/me/change-password", {
      current_password,
      new_password,
    });
  },

  // Consent Preferences
  async updateConsentPreferences(preferences: {
    data_collection?: boolean;
    model_training?: boolean;
    analytics?: boolean;
  }) {
    const { data } = await apiClient.patch("/users/me/consent", preferences);
    return data;
  },

  // Admin endpoints
  async getAdminStats() {
    const { data } = await apiClient.get("/admin/stats");
    return data;
  },

  async getAllCustomers(page: number = 1, limit: number = 50) {
    const { data } = await apiClient.get(`/admin/customers?page=${page}&limit=${limit}`);
    return data;
  },

  async getCustomerDetails(customer_id: string) {
    const { data } = await apiClient.get(`/admin/customers/${customer_id}`);
    return data;
  },

  async updateCustomerTier(customer_id: string, tier: string) {
    const { data } = await apiClient.patch(`/admin/customers/${customer_id}/tier`, { tier });
    return data;
  },

  async getAllSafetyIncidents(page: number = 1, limit: number = 50, severity?: string) {
    const params = severity ? `?page=${page}&limit=${limit}&severity=${severity}` : `?page=${page}&limit=${limit}`;
    const { data } = await apiClient.get(`/admin/safety/incidents${params}`);
    return data;
  },

  async getSystemHealth() {
    const { data } = await apiClient.get("/admin/monitoring/health");
    return data;
  },

  async getGPUMetrics() {
    const { data } = await apiClient.get("/admin/monitoring/gpu");
    return data;
  },
};
