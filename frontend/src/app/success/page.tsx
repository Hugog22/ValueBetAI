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
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-[#1B365D] to-transparent"></div>
            
            {status === 'loading' ? (
                <div className="flex flex-col items-center py-12">
                    <div className="w-12 h-12 border-4 border-slate-300 border-t-[#1B365D] rounded-full animate-spin mb-6"></div>
                    <h2 className="text-xl font-bold text-slate-900 mb-2">Verificando tu pago...</h2>
                    <p className="text-[#94a3b8] text-sm">Por favor, no cierres esta ventana.</p>
                </div>
            ) : status === 'error' ? (
                <div className="flex flex-col items-center py-8 transform transition-all animate-fade-in-up">
                    <div className="w-20 h-20 bg-red-900/30 rounded-full flex items-center justify-center text-red-500 mb-6 shadow-[0_0_30px_rgba(239,68,68,0.2)]">
                        <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </div>
                    <h2 className="text-3xl font-editorial font-bold text-slate-900 mb-4">Error de Pago</h2>
                    <p className="text-[#94a3b8] mb-8">
                        {errorMsg}
                    </p>
                    <Link href="/pricing" className="w-full block py-4 rounded-xl bg-white/10 text-slate-900 font-bold hover:bg-white/20 transition-colors">
                        Volver a Intentar
                    </Link>
                </div>
            ) : (
                <div className="flex flex-col items-center py-8 transform transition-all animate-fade-in-up">
                    <div className="w-20 h-20 bg-slate-200 rounded-full flex items-center justify-center text-[#1B365D] mb-6 shadow-lg">
                        <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7"></path>
                        </svg>
                    </div>
                    <h2 className="text-3xl font-editorial font-bold text-slate-900 mb-4">¡Suscripción Activa!</h2>
                    <p className="text-[#94a3b8] mb-8">
                        Bienvenido a QuantStake Premium. Tu cuenta ha sido actualizada y ya tienes acceso a todas las predicciones y análisis.
                    </p>
                    <Link href="/dashboard" className="w-full block py-4 rounded-xl bg-[#1B365D] text-white font-bold hover:bg-[#132845] transition-colors shadow-md">
                        Ir a mi Dashboard
                    </Link>
                </div>
            )}
        </div>
    );
}

export default function SuccessPage() {
    return (
        <div className="min-h-screen bg-[#F8FAFC] flex flex-col items-center justify-center p-4">
            <Suspense fallback={
                <div className="max-w-md w-full bg-white/5 border border-white/10 rounded-3xl p-8 text-center relative overflow-hidden">
                    <div className="flex flex-col items-center py-12">
                        <div className="w-12 h-12 border-4 border-slate-300 border-t-[#1B365D] rounded-full animate-spin mb-6"></div>
                        <h2 className="text-xl font-bold text-slate-900 mb-2">Cargando...</h2>
                    </div>
                </div>
            }>
                <SuccessContent />
            </Suspense>
        </div>
    );
}
