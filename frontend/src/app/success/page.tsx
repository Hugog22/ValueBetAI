'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';

import { Suspense } from 'react';

function SuccessContent() {
    const [status, setStatus] = useState('loading');
    const searchParams = useSearchParams();
    const { token } = useAuth();
    const [errorMsg, setErrorMsg] = useState('');

    useEffect(() => {
        const sessionId = searchParams.get('session_id');
        if (!sessionId) {
            setStatus('error');
            setErrorMsg('No se encontró el identificador de sesión.');
            return;
        }

        if (!token) {
            // Give AuthContext a moment to load token
            const timer = setTimeout(() => {
                const storedToken = localStorage.getItem('auth_token');
                if (!storedToken) {
                    setStatus('error');
                    setErrorMsg('No estás autenticado.');
                }
            }, 1000);
            return () => clearTimeout(timer);
        }

        const verify = async () => {
            try {
                const API = '/api/proxy';
                const res = await fetch(`${API}/stripe/verify-session?session_id=${sessionId}`);
                
                if (!res.ok) throw new Error('Error al verificar');
                const data = await res.json();
                
                if (data.status === 'paid') {
                    setStatus('success');
                } else {
                    setStatus('error');
                    setErrorMsg('El pago no ha sido completado.');
                }
            } catch (err) {
                setStatus('error');
                setErrorMsg('No se pudo verificar el pago en este momento. Si te han cobrado, el acceso se activará en breve.');
            }
        };

        verify();
    }, [searchParams, token]);

    return (
        <div className="max-w-md w-full bg-white/5 border border-white/10 rounded-3xl p-8 text-center relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-[#C0FF00] to-transparent"></div>
            
            {status === 'loading' ? (
                <div className="flex flex-col items-center py-12">
                    <div className="w-12 h-12 border-4 border-[#064E3B] border-t-[#C0FF00] rounded-full animate-spin mb-6"></div>
                    <h2 className="text-xl font-bold text-white mb-2">Verificando tu pago...</h2>
                    <p className="text-[#94a3b8] text-sm">Por favor, no cierres esta ventana.</p>
                </div>
            ) : status === 'error' ? (
                <div className="flex flex-col items-center py-8 transform transition-all animate-fade-in-up">
                    <div className="w-20 h-20 bg-red-900/30 rounded-full flex items-center justify-center text-red-500 mb-6 shadow-[0_0_30px_rgba(239,68,68,0.2)]">
                        <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </div>
                    <h2 className="text-3xl font-editorial font-bold text-white mb-4">Error de Pago</h2>
                    <p className="text-[#94a3b8] mb-8">
                        {errorMsg}
                    </p>
                    <Link href="/pricing" className="w-full block py-4 rounded-xl bg-white/10 text-white font-bold hover:bg-white/20 transition-colors">
                        Volver a Intentar
                    </Link>
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
    );
}

export default function SuccessPage() {
    return (
        <div className="min-h-screen bg-[#051209] flex flex-col items-center justify-center p-4">
            <Suspense fallback={
                <div className="max-w-md w-full bg-white/5 border border-white/10 rounded-3xl p-8 text-center relative overflow-hidden">
                    <div className="flex flex-col items-center py-12">
                        <div className="w-12 h-12 border-4 border-[#064E3B] border-t-[#C0FF00] rounded-full animate-spin mb-6"></div>
                        <h2 className="text-xl font-bold text-white mb-2">Cargando...</h2>
                    </div>
                </div>
            }>
                <SuccessContent />
            </Suspense>
        </div>
    );
}
