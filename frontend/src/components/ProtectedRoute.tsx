'use client';

import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
    const { user, token, isLoading, isValidating, logout } = useAuth();
    const router = useRouter();
    const [isCheckoutLoading, setIsCheckoutLoading] = useState(false);

    useEffect(() => {
        if (!isLoading && !token) {
            router.push('/login');
        }
    }, [token, isLoading, router]);

    const handleCheckout = async () => {
        setIsCheckoutLoading(true);
        try {
            const checkoutRes = await fetch(`/api/proxy/stripe/create-checkout-session`, {
                method: 'POST',
                
            });
            if (checkoutRes.ok) {
                const checkoutData = await checkoutRes.json();
                window.location.href = checkoutData.url;
            } else {
                alert('No se pudo iniciar la sesión de pago. Por favor, inténtalo más tarde.');
                setIsCheckoutLoading(false);
            }
        } catch (err) {
            console.error(err);
            setIsCheckoutLoading(false);
        }
    };

    if (isLoading || !token || isValidating) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-[#FCF9F1]">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#064E3B]"></div>
            </div>
        );
    }

    return (
        <>
            {user?.subscription_status === 'trialing' && (
                <div className="fixed bottom-0 left-0 right-0 z-50 bg-gradient-to-r from-[#064E3B] to-[#0a7c5c] text-white py-3 px-6 flex items-center justify-center gap-4 shadow-[0_-4px_20px_rgba(6,78,59,0.3)]">
                    <div className="w-2 h-2 rounded-full bg-[#C0FF00] animate-pulse shrink-0" />
                    <p className="text-sm font-semibold">
                        🎉 <span className="font-black">Prueba gratuita activa</span> — Disfruta de 7 días gratis. Tu primer cobro será al finalizar el período de prueba.
                    </p>
                    <button
                        onClick={handleCheckout}
                        className="ml-auto shrink-0 px-4 py-1.5 bg-[#C0FF00] text-[#051209] text-xs font-black uppercase tracking-widest rounded-full hover:bg-[#a3d900] transition-colors"
                    >
                        Gestionar
                    </button>
                </div>
            )}
            {children}
        </>
    );
}
