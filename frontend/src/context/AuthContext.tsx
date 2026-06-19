'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';

interface User {
    id: number;
    email: string;
    subscription_status?: string | null;
    is_admin?: boolean;
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    login: (redirect?: boolean) => void;
    logout: () => void;
    isLoading: boolean;
    isValidating: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isValidating, setIsValidating] = useState(true);
    const router = useRouter();

    const fetchUser = async () => {
        setIsValidating(true);
        try {
            const response = await fetch('/api/proxy/auth/me');
            if (response.ok) {
                const userData = await response.json();
                setUser(userData);
            } else {
                setUser(null);
            }
        } catch {
            console.warn('[AuthContext] Network error fetching user');
        } finally {
            setIsLoading(false);
            setIsValidating(false);
        }
    };

    useEffect(() => {
        fetchUser();
    }, []);

    const login = async (redirect: boolean = true) => {
        setIsLoading(true);
        await fetchUser();
        if (redirect) {
            router.push('/dashboard');
        }
    };

    const logout = async () => {
        await fetch('/api/auth/logout', { method: 'POST' });
        setUser(null);
        router.push('/login');
    };

    const token = user ? "active" : null;

    return (
        <AuthContext.Provider value={{ user, token, login, logout, isLoading, isValidating }}>
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
