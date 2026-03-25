'use client';

import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
    const { token, isLoading } = useAuth();
    const router = useRouter();

    useEffect(() => {
        if (!isLoading && !token) {
            router.push('/login');
        }
    }, [token, isLoading, router]);

    if (isLoading || !token) {
        return <div className="min-h-screen flex items-center justify-center bg-gray-50 text-gray-500 font-bold">Cargando...</div>;
    }

    return <>{children}</>;
}
