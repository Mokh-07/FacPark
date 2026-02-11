import axios from 'axios';
import { toast } from 'react-hot-toast';

// Base URL points to standard Vite proxy or explicit localhost
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Request Interceptor: Add Token
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Response Interceptor: Handle Errors (401 -> Refresh or Logout)
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        // Check if error is 401 and we haven't retried yet
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;
            const refreshToken = localStorage.getItem('refresh_token');

            if (refreshToken) {
                try {
                    // Attempt to refresh token
                    const { data } = await axios.post(`${API_URL}/auth/refresh`, {
                        refresh_token: refreshToken
                    });

                    // Save new tokens
                    localStorage.setItem('access_token', data.access_token);
                    localStorage.setItem('refresh_token', data.refresh_token);

                    // Update header and retry
                    originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
                    return api(originalRequest);
                } catch (refreshError) {
                    // Refresh failed - clean up and redirect to login
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('refresh_token');
                    toast.error("Session expirée, veuillez vous reconnecter.");
                    window.location.href = '/login';
                    return Promise.reject(refreshError);
                }
            } else {
                // No refresh token available
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                window.location.href = '/login';
            }
        }

        // Handle other errors
        const errorMessage = error.response?.data?.detail || error.response?.data?.message || "Une erreur est survenue";
        if (error.response?.status !== 401) { // Avoid spamming toasts for 401
            toast.error(errorMessage);
        }

        return Promise.reject(error);
    }
);

export default api;
