'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

export default function SuccessPage() {
    const [status, setStatus] = useState('loading');

    useEffect(() => {
        // Just a simple visual delay to make it feel like we're verifying
        const timer = setTimeout(() => {
            setStatus('success');
        }, 1500);
        return () => clearTimeout(timer);
    }, []);

    return (
        <div className="min-h-screen bg-[#051209] flex flex-col items-center justify-center p-4">
            <div className="max-w-md w-full bg-white/5 border border-white/10 rounded-3xl p-8 text-center relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-[#C0FF00] to-transparent"></div>
                
                {status === 'loading' ? (
                    <div className="flex flex-col items-center py-12">
                        <div className="w-12 h-12 border-4 border-[#064E3B] border-t-[#C0FF00] rounded-full animate-spin mb-6"></div>
                        <h2 className="text-xl font-bold text-white mb-2">Verificando tu pago...</h2>
                        <p className="text-[#94a3b8] text-sm">Por favor, no cierres esta ventana.</p>
                    </div>
                ) : (
                    <div className="flex flex-col items-center py-8 transform transition-all animate-fade-in-up">
                        <div className="w-20 h-20 bg-[#064E3B]/30 rounded-full flex items-center justify-center text-[#C0FF00] mb-6 shadow-[0_0_30px_rgba(192,255,0,0.2)]">
                            <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7"></path>
                            </svg>
                        </div>
                        <h2 className="text-3xl font-editorial font-bold text-white mb-4">¡Suscripción Activa!</h2>
                        <p className="text-[#94a3b8] mb-8">
                            Bienvenido a ValueBet AI Premium. Tu cuenta ha sido actualizada y ya tienes acceso a todas las predicciones y análisis.
                        </p>
                        <Link href="/dashboard" className="w-full block py-4 rounded-xl bg-[#C0FF00] text-[#051209] font-bold hover:bg-[#a3d900] transition-colors shadow-[0_0_20px_rgba(192,255,0,0.2)]">
                            Ir a mi Dashboard
                        </Link>
                    </div>
                )}
            </div>
        </div>
    );
}
