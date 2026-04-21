'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';

interface User {
    id: number;
    email: string;
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    login: (token: string) => void;
    logout: () => void;
    isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * Decode the payload of a JWT token without verifying the signature.
 * The signature is always verified server-side on every protected request.
 * This is safe for client-side UX purposes (extracting email / user id).
 */
function parseJwtPayload(token: string): { sub?: string; id?: number } | null {
    try {
        const parts = token.split('.');
        if (parts.length !== 3) return null;
        // Base64url → Base64 → JSON
        const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
        const json = atob(base64);
        return JSON.parse(json);
    } catch {
        return null;
    }
}

export const AuthProvider = ({ children }: { children: ReactNode }) => {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        const storedToken = localStorage.getItem('auth_token');
        if (storedToken) {
            // Fast-path: decode locally and set user immediately so the app
            // renders without waiting for a network round-trip.
            const payload = parseJwtPayload(storedToken);
            if (payload?.sub) {
                setToken(storedToken);
                setUser({ id: payload.id ?? 0, email: payload.sub });
                setIsLoading(false);
                // Validate in background — logs out silently if token expired
                validateTokenInBackground(storedToken);
            } else {
                // Malformed token — clear it
                localStorage.removeItem('auth_token');
                setIsLoading(false);
            }
        } else {
            setIsLoading(false);
        }
    }, []);

    /**
     * Silently verify the token server-side without blocking the UI.
     * If invalid/expired, logs out the user gracefully.
     */
    const validateTokenInBackground = async (authToken: string) => {
        try {
            const response = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/auth/me`,
                { headers: { Authorization: `Bearer ${authToken}` } }
            );
            if (response.ok) {
                const userData = await response.json();
                // Update with full server data (e.g. confirmed id)
                setUser(userData);
            } else {
                // Token rejected by server (expired, revoked) — logout
                logout();
            }
        } catch {
            // Network error — keep user logged in locally, retry will happen later
            console.warn('[AuthContext] Background token validation failed (network). Keeping session.');
        }
    };

    const login = (newToken: string) => {
        localStorage.setItem('auth_token', newToken);
        setToken(newToken);

        // Decode immediately — no extra network call needed
        const payload = parseJwtPayload(newToken);
        if (payload?.sub) {
            setUser({ id: payload.id ?? 0, email: payload.sub });
        }

        // Navigate FIRST, then confirm user data in background
        router.push('/');
        validateTokenInBackground(newToken);
    };

    const logout = () => {
        localStorage.removeItem('auth_token');
        setToken(null);
        setUser(null);
        router.push('/login');
    };

    return (
        <AuthContext.Provider value={{ user, token, login, logout, isLoading }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
