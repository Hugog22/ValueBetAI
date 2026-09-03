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

    const isSubscribed = user?.subscription_status === 'active' || user?.subscription_status === 'trialing';

    if (!isSubscribed) {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-[#FCF9F1] px-4 text-center">
                <div className="bg-white p-10 rounded-[2.5rem] border border-[#E5E7EB] shadow-[0_20px_50px_rgba(0,0,0,0.04)] max-w-md w-full">
                    <div className="w-16 h-16 bg-[#FEE2E2] rounded-full flex items-center justify-center mx-auto mb-6 text-red-600">
                        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
                        </svg>
                    </div>
                    <h2 className="text-2xl font-editorial font-bold text-[#1A1C1E] mb-4">Suscripción Inactiva</h2>
                    <p className="text-[#64748B] mb-8 text-sm leading-relaxed">
                        Parece que tu pago no se completó o tu suscripción ha expirado. Para acceder al radar de QuantStake necesitas una suscripción activa.
                    </p>
                    <button
                        onClick={handleCheckout}
                        disabled={isCheckoutLoading}
                        className="w-full flex justify-center items-center py-4 px-4 bg-[#064E3B] text-white text-xs uppercase tracking-[0.2em] font-black rounded-2xl hover:bg-[#043327] shadow-xl shadow-[#064E3B]/20 transition-all active:scale-95 group disabled:opacity-50"
                    >
                        {isCheckoutLoading ? 'Cargando...' : 'Activar Suscripción'}
                        {!isCheckoutLoading && (
                            <svg className="w-4 h-4 ml-3 transition-transform group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                            </svg>
                        )}
                    </button>
                    
                    <div className="mt-6 text-center">
                        <button onClick={() => logout()} className="text-[10px] uppercase tracking-[0.2em] font-black text-[#64748B] hover:text-[#064E3B] transition-colors inline-flex items-center gap-2">
                            <span>¿Usar otra cuenta?</span>
                            <span className="text-[#064E3B] border-b-2 border-[#FFD700]">Cerrar sesión</span>
                        </button>
                    </div>
                </div>
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
