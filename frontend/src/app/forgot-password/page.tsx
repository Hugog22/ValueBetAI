'use client';

import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState('');
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setMessage('');
        setIsLoading(true);

        try {
            const res = await fetch(`/api/proxy/auth/forgot-password`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email })
            });

            const data = await res.json();
            
            if (!res.ok) {
                throw new Error(data.detail || 'Error al procesar la solicitud');
            }

            setMessage(data.message || 'Si el email existe, se ha enviado un enlace de recuperación.');
            setEmail('');
        } catch (err: any) {
            setError(err.message || 'Error de conexión');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-[#FCF9F1] py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden font-sans">
            
            {/* Background Texture/Art */}
            <div className="absolute top-0 right-0 w-1/2 h-full bg-[#064E3B]/[0.02] -skew-x-12 transform origin-top-right"></div>
            
            {/* Back Button */}
            <Link href="/login" className="absolute top-8 left-8 flex items-center gap-2 text-[#64748B] hover:text-[#1A1C1E] transition-colors z-20 group">
                <svg className="w-5 h-5 transition-transform group-hover:-translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                <span className="text-xs font-bold uppercase tracking-wider">Volver a Login</span>
            </Link>
            
            <div className="max-w-md w-full z-10">
                <div className="text-center mb-12">
                    <Link href="/" className="inline-flex flex-col items-center gap-3 group">
                        <Image src="/logo.png" alt="QuantStake Logo" width={240} height={70} className="h-16 w-auto object-contain group-hover:scale-105 transition-transform" priority />
                    </Link>
                    <h2 className="mt-8 text-4xl font-editorial font-bold text-[#1A1C1E]">
                        Recuperar <span className="italic font-light">Acceso</span>
                    </h2>
                    <p className="mt-4 text-[10px] uppercase tracking-[0.3em] font-bold text-[#64748B]">
                        Introduce tu correo electrónico
                    </p>
                </div>

                <div className="bg-white p-10 rounded-[2.5rem] border border-[#E5E7EB] shadow-[0_20px_50px_rgba(0,0,0,0.04)]">
                    <form className="space-y-6" onSubmit={handleSubmit}>
                        {error && (
                            <div className="bg-red-50 border border-red-100 text-red-600 px-4 py-3 rounded-2xl text-xs font-bold uppercase tracking-widest text-center" role="alert">
                                {error}
                            </div>
                        )}
                        {message && (
                            <div className="bg-green-50 border border-green-100 text-green-700 px-4 py-3 rounded-2xl text-xs font-bold uppercase tracking-widest text-center" role="alert">
                                {message}
                            </div>
                        )}

                        <div className="space-y-6">
                            <div>
                                <label className="text-[10px] uppercase tracking-[0.2em] font-black text-[#64748B] block mb-2 ml-1">Correo Electrónico</label>
                                <input
                                    id="email"
                                    name="email"
                                    type="email"
                                    required
                                    className="appearance-none block w-full px-5 py-4 bg-[#F8F9FA] border border-[#E5E7EB] placeholder-[#94A3B8] text-[#1A1C1E] rounded-2xl focus:outline-none focus:border-[#064E3B] focus:ring-1 focus:ring-[#064E3B] transition-all font-medium"
                                    placeholder="inversor@quantstake.ai"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="pt-4">
                            <button
                                type="submit"
                                disabled={isLoading}
                                className="w-full flex justify-center items-center py-5 px-4 bg-[#064E3B] text-white text-xs uppercase tracking-[0.2em] font-black rounded-2xl hover:bg-[#043327] shadow-xl shadow-[#064E3B]/20 transition-all active:scale-95 group disabled:opacity-70 disabled:cursor-not-allowed"
                            >
                                {isLoading ? 'Enviando...' : 'Enviar Enlace'}
                                {!isLoading && (
                                    <svg className="w-4 h-4 ml-3 transition-transform group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                                    </svg>
                                )}
                            </button>
                        </div>
                    </form>
                </div>

                <p className="mt-12 text-center text-[#94A3B8] text-[9px] uppercase tracking-[0.4em] font-medium">
                    Sistemas de Inversión QuantStake &copy; 2026
                </p>
            </div>
        </div>
    );
}
