import axios from 'axios';

// Base API URL configuration
// In production on Render/Vercel, VITE_API_URL points to the backend web service URL.
// In local development, VITE_API_URL defaults to 'http://127.0.0.1:8000'.
export const getBaseUrl = () => {
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl) {
    return envUrl.replace(/\/+$/, '');
  }
  return 'http://127.0.0.1:8000';
};

export const API_BASE_URL = getBaseUrl();

export const resolveImageUrl = (url) => {
  if (!url) return null;
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) {
    return url;
  }
  const base = getBaseUrl();
  return `${base}${url.startsWith('/') ? '' : '/'}${url}`;
};

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
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

// Helper function to extract user-friendly error messages from FastAPI responses
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
        return 'Validation error. Please verify all required fields.';
      case 500:
        return 'Internal server error. Please try again later.';
      case 503:
        return 'Database service temporarily unavailable. Please try again in a moment.';
      default:
        return `Request failed with status ${status}`;
    }
  }

  if (error.request) {
    return 'Unable to reach the server. Please verify the backend is running.';
  }

  return error.message || 'Network error';
};

// Response interceptor to handle 401 unauthorized globally
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
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

// Profile & User Settings API
export const profileAPI = {
  getProfile: async () => {
    const response = await apiClient.get('/users/me');
    return response.data;
  },

  updateProfile: async (profileData) => {
    const response = await apiClient.put('/users/profile', profileData);
    return response.data;
  },

  changePassword: async (passwordData) => {
    const response = await apiClient.put('/users/change-password', passwordData);
    return response.data;
  },
};

// Trips API services
export const tripsAPI = {
  getTrips: async (userId) => {
    const response = await apiClient.get(`/trips/${userId}`);
    return response.data;
  },

  getSingleTrip: async (tripId) => {
    const response = await apiClient.get(`/trips/single/${tripId}`);
    return response.data;
  },

  createTrip: async (tripData) => {
    const payload = {
      user_id: tripData.user_id,
      destination: tripData.destination.trim(),
      title: tripData.title ? tripData.title.trim() : undefined,
      start_date: tripData.start_date,
      end_date: tripData.end_date,
      status: tripData.status || 'planned',
      budget: parseFloat(tripData.budget) || 0,
      description: tripData.description || '',
      travelers: parseInt(tripData.travelers, 10) || 1,
      notes: tripData.notes || '',
    };
    const response = await apiClient.post('/trips/', payload);
    return response.data;
  },

  updateTrip: async (tripId, tripData) => {
    const payload = {};
    if (tripData.destination !== undefined) payload.destination = tripData.destination.trim();
    if (tripData.title !== undefined) payload.title = tripData.title ? tripData.title.trim() : null;
    if (tripData.start_date !== undefined) payload.start_date = tripData.start_date;
    if (tripData.end_date !== undefined) payload.end_date = tripData.end_date;
    if (tripData.status !== undefined) payload.status = tripData.status;
    if (tripData.budget !== undefined) payload.budget = parseFloat(tripData.budget) || 0;
    if (tripData.description !== undefined) payload.description = tripData.description;
    if (tripData.travelers !== undefined) payload.travelers = parseInt(tripData.travelers, 10) || 1;
    if (tripData.notes !== undefined) payload.notes = tripData.notes;

    const response = await apiClient.put(`/trips/${tripId}`, payload);
    return response.data;
  },

  deleteTrip: async (tripId) => {
    const response = await apiClient.delete(`/trips/${tripId}`);
    return response.data;
  },
};

// Day-by-day Itinerary API services
export const itineraryAPI = {
  getTripActivities: async (tripId) => {
    const response = await apiClient.get(`/itinerary/trip/${tripId}`);
    return response.data;
  },

  createActivity: async (activityData) => {
    const payload = {
      trip_id: activityData.trip_id,
      day_number: parseInt(activityData.day_number, 10) || 1,
      date: activityData.date,
      time: activityData.time || '',
      title: activityData.title.trim(),
      location: activityData.location || '',
      description: activityData.description || '',
      cost: parseFloat(activityData.cost) || 0,
      notes: activityData.notes || '',
    };
    const response = await apiClient.post('/itinerary/', payload);
    return response.data;
  },

  updateActivity: async (activityId, activityData) => {
    const payload = {};
    if (activityData.day_number !== undefined) payload.day_number = parseInt(activityData.day_number, 10) || 1;
    if (activityData.date !== undefined) payload.date = activityData.date;
    if (activityData.time !== undefined) payload.time = activityData.time;
    if (activityData.title !== undefined) payload.title = activityData.title.trim();
    if (activityData.location !== undefined) payload.location = activityData.location;
    if (activityData.description !== undefined) payload.description = activityData.description;
    if (activityData.cost !== undefined) payload.cost = parseFloat(activityData.cost) || 0;
    if (activityData.notes !== undefined) payload.notes = activityData.notes;

    const response = await apiClient.put(`/itinerary/${activityId}`, payload);
    return response.data;
  },

  deleteActivity: async (activityId) => {
    const response = await apiClient.delete(`/itinerary/${activityId}`);
    return response.data;
  },
};

// Budget & Expense API services
export const expensesAPI = {
  getTripExpenses: async (tripId) => {
    const response = await apiClient.get(`/expenses/trip/${tripId}`);
    return response.data;
  },

  getUserExpenseSummary: async (userId) => {
    const response = await apiClient.get(`/expenses/user/${userId}/summary`);
    return response.data;
  },

  createExpense: async (expenseData) => {
    const payload = {
      trip_id: expenseData.trip_id,
      category: expenseData.category,
      amount: parseFloat(expenseData.amount) || 0,
      date: expenseData.date,
      description: expenseData.description.trim(),
    };
    const response = await apiClient.post('/expenses/', payload);
    return response.data;
  },

  updateExpense: async (expenseId, expenseData) => {
    const payload = {};
    if (expenseData.category !== undefined) payload.category = expenseData.category;
    if (expenseData.amount !== undefined) payload.amount = parseFloat(expenseData.amount) || 0;
    if (expenseData.date !== undefined) payload.date = expenseData.date;
    if (expenseData.description !== undefined) payload.description = expenseData.description.trim();

    const response = await apiClient.put(`/expenses/${expenseId}`, payload);
    return response.data;
  },

  deleteExpense: async (expenseId) => {
    const response = await apiClient.delete(`/expenses/${expenseId}`);
    return response.data;
  },
};

// AI Trip Planner and Budget Assistant API
export const aiAPI = {
  planTrip: async (tripPlanRequest) => {
    const response = await apiClient.post('/ai/plan-trip', tripPlanRequest);
    return response.data;
  },

  getBudgetAdvice: async (tripId) => {
    const response = await apiClient.post('/ai/budget-advice', { trip_id: tripId });
    return response.data;
  },
};

// Explore & Travel Discovery API
export const exploreAPI = {
  getFeatured: async () => {
    const response = await apiClient.get('/explore/featured');
    return response.data;
  },

  search: async (query, category = 'all', limit = 30) => {
    const response = await apiClient.get('/explore/search', {
      params: { q: query, category, limit },
    });
    return response.data;
  },

  getDestination: async (destination) => {
    const response = await apiClient.get(`/explore/destinations/${encodeURIComponent(destination)}`);
    return response.data;
  },

  getPlaceDetails: async (placeId) => {
    const response = await apiClient.get(`/explore/places/${encodeURIComponent(placeId)}`);
    return response.data;
  },

  getHotels: async (query, limit = 30) => {
    const response = await apiClient.get('/explore/hotels', {
      params: { q: query, limit },
    });
    return response.data;
  },

  getRestaurants: async (query, limit = 30) => {
    const response = await apiClient.get('/explore/restaurants', {
      params: { q: query, limit },
    });
    return response.data;
  },

  getAttractions: async (query, limit = 30) => {
    const response = await apiClient.get('/explore/attractions', {
      params: { q: query, limit },
    });
    return response.data;
  },
};

// Wishlist API services
export const wishlistAPI = {
  getWishlist: async () => {
    const response = await apiClient.get('/wishlist/');
    return response.data;
  },

  addToWishlist: async (itemData) => {
    const payload = {
      place_id: itemData.place_id,
      name: itemData.name,
      category: itemData.category || 'destination',
      location: itemData.location,
      image_url: itemData.image_url,
      rating: itemData.rating !== undefined ? itemData.rating : null,
      description: itemData.description,
      metadata: itemData.metadata || {},
    };
    const response = await apiClient.post('/wishlist/', payload);
    return response.data;
  },

  checkSaved: async (placeId) => {
    const response = await apiClient.get(`/wishlist/check/${encodeURIComponent(placeId)}`);
    return response.data;
  },

  removeFromWishlist: async (wishlistId) => {
    const response = await apiClient.delete(`/wishlist/${wishlistId}`);
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
