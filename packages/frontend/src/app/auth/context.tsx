/**
 * Authentication context for managing user authentication state.
 */

import React, { createContext, useCallback, useEffect, useState } from 'react';
import {
    login as apiLogin,
    register as apiRegister,
    getCurrentUser,
    loginWithGithub,
    User,
} from '../api';

interface AuthContextType {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (email: string, password: string) => Promise<void>;
    register: (email: string, password: string) => Promise<void>;
    loginWithGithub: (code: string, state: string) => Promise<void>;
    logout: () => void;
    getGithubOAuthUrl: () => Promise<{ oauth_url: string; state: string }>;
    refreshUser: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | null>(null);

const TOKEN_KEY = 'starmind_token';

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    const refreshUser = useCallback(async () => {
        const token = localStorage.getItem(TOKEN_KEY);
        if (!token) {
            setUser(null);
            setIsLoading(false);
            return;
        }

        try {
            const userData = await getCurrentUser();
            setUser(userData);
        } catch (error) {
            console.error('Failed to fetch user:', error);
            localStorage.removeItem(TOKEN_KEY);
            setUser(null);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        refreshUser();
    }, [refreshUser]);

    const login = useCallback(async (email: string, password: string) => {
        const response = await apiLogin(email, password);
        localStorage.setItem(TOKEN_KEY, response.access_token);
        setUser(response.user);
    }, []);

    const register = useCallback(async (email: string, password: string) => {
        const response = await apiRegister(email, password);
        localStorage.setItem(TOKEN_KEY, response.access_token);
        setUser(response.user);
    }, []);

    const handleGithubLogin = useCallback(async (code: string, state: string) => {
        const response = await loginWithGithub(code, state);
        localStorage.setItem(TOKEN_KEY, response.access_token);
        setUser(response.user);
    }, []);

    const logout = useCallback(() => {
        localStorage.removeItem(TOKEN_KEY);
        setUser(null);
    }, []);

    const getGithubOAuthUrl = useCallback(async () => {
        const response = await fetch('/api/auth/github');
        if (!response.ok) {
            throw new Error('Failed to get GitHub OAuth URL');
        }
        return response.json();
    }, []);

    return (
        <AuthContext.Provider
            value={{
                user,
                isAuthenticated: !!user,
                isLoading,
                login,
                register,
                loginWithGithub: handleGithubLogin,
                logout,
                getGithubOAuthUrl,
                refreshUser,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = React.useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
