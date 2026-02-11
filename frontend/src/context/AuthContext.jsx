import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';
import { toast } from 'react-hot-toast';
import { jwtDecode } from "jwt-decode";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    // Check auth status on mount
    useEffect(() => {
        const checkAuth = async () => {
            const token = localStorage.getItem('access_token');
            if (token) {
                try {
                    // Verify token validity via /me endpoint
                    const { data } = await api.get('/auth/me');
                    setUser(data);
                } catch (error) {
                    console.error("Auth check failed:", error);
                    // Only clear if 401/403 (handled by interceptor mostly, but safe fallback)
                    if (error.response?.status === 401) {
                        logout(false);
                    }
                }
            }
            setLoading(false);
        };
        checkAuth();
    }, []);

    const login = async (email, password) => {
        try {
            // Utilisation de URLSearchParams pour 'application/x-www-form-urlencoded'
            // C'est le standard attendu par OAuth2PasswordRequestForm de FastAPI
            const params = new URLSearchParams();
            params.append('username', email); // Le backend attend 'username'
            params.append('password', password);

            const { data } = await api.post('/auth/login', params, {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            });

            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('refresh_token', data.refresh_token);

            // Store user info for chat history separation
            localStorage.setItem('user', JSON.stringify(data.user));

            setUser(data.user);
            toast.success(`Bienvenue, ${data.user.full_name} !`);
            return data.user;
        } catch (error) {
            console.error("Login error:", error);
            return null;
        }
    };

    const logout = (notify = true) => {
        // Get current user before clearing for chat history key
        const currentUser = localStorage.getItem('user');

        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');

        setUser(null);
        if (notify) toast.success("Déconnexion réussie");
    };

    const isAdmin = () => user?.role === 'ADMIN';

    return (
        <AuthContext.Provider value={{ user, login, logout, isAdmin, loading }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
