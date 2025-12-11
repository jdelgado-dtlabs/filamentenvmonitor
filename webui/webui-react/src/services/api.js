/**
 * API service layer for FilamentBox backend
 */

const API_BASE = import.meta.env.VITE_API_URL || window.location.origin;

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function fetchApi(endpoint, options = {}) {
  const url = `${API_BASE}/api/${endpoint}`;
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    const data = await response.json();

    if (!response.ok) {
      throw new ApiError(
        data.error || `HTTP error! status: ${response.status}`,
        response.status,
        data
      );
    }

    return data;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(error.message, 0, null);
  }
}

export const api = {
  // Status endpoints
  getStatus: () => fetchApi('status'),
  getDatabase: () => fetchApi('database'),
  getThreads: () => fetchApi('threads'),

  // Configuration endpoints
  getConfig: (key) => fetchApi(`config/${key}`),
  setConfig: (key, value, validateOnly = false) =>
    fetchApi(`config/${key}`, {
      method: 'PUT',
      body: JSON.stringify({ value, validate_only: validateOnly }),
    }),
  getConfigSection: (section) => fetchApi(`config/section/${section}`),

  // Control endpoints
  controlDevice: (device, state) =>
    fetchApi(`controls/${device}`, {
      method: 'POST',
      body: JSON.stringify({ state }),
    }),

  // Thread management
  restartThread: (threadName) =>
    fetchApi(`threads/${threadName}/restart`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),
  
  startThread: (threadName) =>
    fetchApi(`threads/${threadName}/start`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),
  
  stopThread: (threadName) =>
    fetchApi(`threads/${threadName}/stop`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),

  // Notifications
  getNotifications: (limit = 10) => fetchApi(`notifications?limit=${limit}`),
  clearNotifications: () => fetchApi('notifications', { method: 'DELETE' }),
};

export { ApiError };
