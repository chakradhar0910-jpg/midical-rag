import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

// In browser: relative URL so Next.js rewrites proxy to backend
// In server components: not used (client-only)
export const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token) config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Auto-refresh on 401
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as any;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) throw new Error('No refresh token');
        const { data } = await axios.post('/api/v1/auth/refresh', {
          refresh_token: refreshToken,
        });
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return apiClient(originalRequest);
      } catch {
        localStorage.clear();
        if (typeof window !== 'undefined') window.location.href = '/auth/login';
      }
    }
    return Promise.reject(error);
  }
);

// ─── Auth ────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data: any) => apiClient.post('/auth/register', data),
  login: (data: any) => apiClient.post('/auth/login', data),
  logout: (refreshToken: string) => apiClient.post('/auth/logout', { refresh_token: refreshToken }),
  refresh: (refreshToken: string) => apiClient.post('/auth/refresh', { refresh_token: refreshToken }),
  forgotPassword: (email: string) => apiClient.post('/auth/forgot-password', { email }),
  resetPassword: (data: any) => apiClient.post('/auth/reset-password', data),
  verifyEmail: (token: string) => apiClient.post('/auth/verify-email', { token }),
  changePassword: (data: any) => apiClient.post('/auth/change-password', data),
  setupMFA: () => apiClient.post('/auth/mfa/setup'),
  enableMFA: (token: string) => apiClient.post('/auth/mfa/enable', { token }),
  disableMFA: (token: string) => apiClient.post('/auth/mfa/disable', { token }),
};

// ─── Users ───────────────────────────────────────────────────────────────────
export const userApi = {
  getProfile: () => apiClient.get('/users/me'),
  updateProfile: (data: any) => apiClient.put('/users/me', data),
  getSettings: () => apiClient.get('/users/me/settings'),
  updateSettings: (data: any) => apiClient.put('/users/me/settings', data),
  getNotifications: (unreadOnly = false) =>
    apiClient.get(`/users/me/notifications?unread_only=${unreadOnly}`),
  markNotificationRead: (id: string) =>
    apiClient.post(`/users/me/notifications/${id}/read`),
  markAllRead: () => apiClient.post('/users/me/notifications/read-all'),
};

// ─── Chat ────────────────────────────────────────────────────────────────────
export const chatApi = {
  list: (params?: any) => apiClient.get('/chats', { params }),
  create: (data?: any) => apiClient.post('/chats', data || { title: 'New Chat' }),
  get: (id: string) => apiClient.get(`/chats/${id}`),
  update: (id: string, data: any) => apiClient.put(`/chats/${id}`, data),
  delete: (id: string) => apiClient.delete(`/chats/${id}`),
  sendMessage: (chatId: string, content: string, provider?: string) =>
    apiClient.post(
      `/chats/${chatId}/messages`,
      { content },
      provider ? { headers: { 'X-AI-Provider': provider } } : undefined
    ),
  getMessages: (chatId: string, params?: any) =>
    apiClient.get(`/chats/${chatId}/messages`, { params }),
  react: (chatId: string, messageId: string, reaction: string) =>
    apiClient.post(`/chats/${chatId}/messages/${messageId}/reaction`, { reaction }),
  export: (chatId: string, format: string) =>
    apiClient.get(`/chats/${chatId}/export?format=${format}`, { responseType: 'blob' }),
};

// ─── AI Provider ────────────────────────────────────────────────────────────
export const aiApi = {
  health: () => apiClient.get('/ai/health'),
  providers: () => apiClient.get('/ai/providers'),
};

// ─── Documents ───────────────────────────────────────────────────────────────
export const documentApi = {
  list: (params?: any) => apiClient.get('/documents', { params }),
  upload: (formData: FormData) =>
    apiClient.post('/documents', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  get: (id: string) => apiClient.get(`/documents/${id}`),
  update: (id: string, data: any) => apiClient.put(`/documents/${id}`, data),
  delete: (id: string) => apiClient.delete(`/documents/${id}`),
  reprocess: (id: string) => apiClient.post(`/documents/${id}/reprocess`),
};

// ─── Admin ───────────────────────────────────────────────────────────────────
export const adminApi = {
  getStats: () => apiClient.get('/admin/stats'),
  getUsers: (params?: any) => apiClient.get('/admin/users', { params }),
  getUser: (id: string) => apiClient.get(`/admin/users/${id}`),
  updateUser: (id: string, data: any) => apiClient.put(`/admin/users/${id}`, data),
  deleteUser: (id: string) => apiClient.delete(`/admin/users/${id}`),
  getLogs: (params?: any) => apiClient.get('/admin/logs', { params }),
  getUsersAnalytics: (days?: number) =>
    apiClient.get('/admin/analytics/users', { params: { days } }),
  getChatsAnalytics: (days?: number) =>
    apiClient.get('/admin/analytics/chats', { params: { days } }),
  getDocuments: (params?: any) => apiClient.get('/admin/documents', { params }),
};
