import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Request interceptor to attach JWT Bearer token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('traveltrack_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Helper function to extract user-friendly error message from FastAPI responses
export const extractErrorMessage = (error) => {
  if (!error) return 'An unexpected error occurred';
  
  if (error.response) {
    const { status, data } = error.response;

    // FastAPI HTTPException details
    if (data && data.detail) {
      if (typeof data.detail === 'string') {
        return data.detail;
      }
      
      // FastAPI Pydantic 422 validation errors array
      if (Array.isArray(data.detail)) {
        return data.detail
          .map((item) => {
            const field = item.loc && item.loc.length > 1 ? `${item.loc[item.loc.length - 1]}: ` : '';
            // Clean common prefixes like 'Value error, '
            const cleanMsg = item.msg ? item.msg.replace(/^Value error,\s*/i, '') : 'Invalid field value';
            return `${field}${cleanMsg}`;
          })
          .join('. ');
      }

      if (typeof data.detail === 'object') {
        return JSON.stringify(data.detail);
      }
    }

    switch (status) {
      case 400:
        return 'Bad request. Please check the provided information.';
      case 401:
        return 'Session expired or unauthorized. Please log in again.';
      case 403:
        return 'Access forbidden. You do not have permission for this resource.';
      case 404:
        return 'Requested resource was not found.';
      case 409:
        return 'Conflict detected. A record with this information already exists.';
      case 422:
        return 'Validation error. Please verify all fields.';
      case 500:
        return 'Internal server error. Please try again later.';
      case 503:
        return 'Service temporarily unavailable. Please verify backend connectivity.';
      default:
        return `Request failed with status ${status}`;
    }
  }

  if (error.request) {
    return 'Unable to reach the server. Please verify the backend is running at ' + API_BASE_URL;
  }

  return error.message || 'Network error';
};

// Response interceptor to handle 401 unauthorized globally
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // If unauthorized on protected routes (not during login attempt)
      const isLoginRequest = error.config?.url?.includes('/users/login');
      if (!isLoginRequest) {
        localStorage.removeItem('traveltrack_token');
        localStorage.removeItem('traveltrack_user');
        window.dispatchEvent(new Event('traveltrack:logout'));
      }
    }
    return Promise.reject(error);
  }
);

// Authentication API services
export const authAPI = {
  register: async (userData) => {
    const response = await apiClient.post('/users/register', {
      name: userData.name.trim(),
      email: userData.email.trim().toLowerCase(),
      password: userData.password,
    });
    return response.data;
  },

  login: async (credentials) => {
    const response = await apiClient.post('/users/login', {
      email: credentials.email.trim().toLowerCase(),
      password: credentials.password,
    });
    return response.data;
  },
};

// Trips API services
export const tripsAPI = {
  getTrips: async (userId) => {
    const response = await apiClient.get(`/trips/${userId}`);
    return response.data;
  },

  createTrip: async (tripData) => {
    const payload = {
      user_id: tripData.user_id,
      destination: tripData.destination.trim(),
      start_date: tripData.start_date,
      end_date: tripData.end_date,
      status: tripData.status || 'planned',
      budget: parseFloat(tripData.budget) || 0,
    };
    const response = await apiClient.post('/trips/', payload);
    return response.data;
  },

  updateTrip: async (tripId, tripData) => {
    const payload = {};
    if (tripData.destination !== undefined) payload.destination = tripData.destination.trim();
    if (tripData.start_date !== undefined) payload.start_date = tripData.start_date;
    if (tripData.end_date !== undefined) payload.end_date = tripData.end_date;
    if (tripData.status !== undefined) payload.status = tripData.status;
    if (tripData.budget !== undefined) payload.budget = parseFloat(tripData.budget) || 0;

    const response = await apiClient.put(`/trips/${tripId}`, payload);
    return response.data;
  },

  deleteTrip: async (tripId) => {
    const response = await apiClient.delete(`/trips/${tripId}`);
    return response.data;
  },
};

// System Health API
export const healthAPI = {
  checkHealth: async () => {
    const response = await apiClient.get('/health');
    return response.data;
  },
};

export default apiClient;
