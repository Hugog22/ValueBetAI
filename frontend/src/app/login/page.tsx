'use client';

import { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function LoginPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const { login } = useAuth();
    const router = useRouter();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        try {
            const formData = new FormData();
            formData.append('username', email);
            formData.append('password', password);

            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/auth/login`, {
                method: 'POST',
                body: formData
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || 'Error al iniciar sesión');
            }

            const data = await res.json();
            login(data.access_token);
        } catch (err: any) {
            setError(err.message || 'Error al iniciar sesión');
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-[#FCF9F1] py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden font-sans">
            
            {/* Background Texture/Art */}
            <div className="absolute top-0 right-0 w-1/2 h-full bg-[#064E3B]/[0.02] -skew-x-12 transform origin-top-right"></div>
            
            <div className="max-w-md w-full z-10">
                <div className="text-center mb-12">
                    <Link href="/" className="inline-flex flex-col items-center gap-3 group">
                        <div className="h-14 w-14 bg-[#FFD700] flex items-center justify-center rounded-2xl shadow-xl shadow-[#FFD700]/20 group-hover:scale-110 transition-transform">
                            <span className="text-[#1A1C1E] font-black text-xs leading-none">BET<br />AI</span>
                        </div>
                        <h1 className="text-3xl font-editorial font-bold text-[#1A1C1E] tracking-tight">
                            ValueBet <span className="opacity-50">AI</span>
                        </h1>
                    </Link>
                    <h2 className="mt-8 text-4xl font-editorial font-bold text-[#1A1C1E]">
                        Bienvenido de <span className="italic font-light">nuevo</span>
                    </h2>
                    <p className="mt-4 text-[10px] uppercase tracking-[0.3em] font-bold text-[#64748B]">
                        Identificación de inversor requerida
                    </p>
                </div>

                <div className="bg-white p-10 rounded-[2.5rem] border border-[#E5E7EB] shadow-[0_20px_50px_rgba(0,0,0,0.04)]">
                    <form className="space-y-6" onSubmit={handleSubmit}>
                        {error && (
                            <div className="bg-red-50 border border-red-100 text-red-600 px-4 py-3 rounded-2xl text-xs font-bold uppercase tracking-widest text-center" role="alert">
                                {error}
                            </div>
                        )}

                        <div className="space-y-6">
                            <div>
                                <label className="text-[10px] uppercase tracking-[0.2em] font-black text-[#64748B] block mb-2 ml-1">Credencial de Acceso (Email)</label>
                                <input
                                    id="email-address"
                                    name="email"
                                    type="email"
                                    required
                                    className="appearance-none block w-full px-5 py-4 bg-[#F8F9FA] border border-[#E5E7EB] placeholder-[#94A3B8] text-[#1A1C1E] rounded-2xl focus:outline-none focus:border-[#064E3B] focus:ring-1 focus:ring-[#064E3B] transition-all font-medium"
                                    placeholder="inversor@valuebet.ai"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                />
                            </div>
                            <div>
                                <label className="text-[10px] uppercase tracking-[0.2em] font-black text-[#64748B] block mb-2 ml-1">Clave de Seguridad</label>
                                <input
                                    id="password"
                                    name="password"
                                    type="password"
                                    required
                                    className="appearance-none block w-full px-5 py-4 bg-[#F8F9FA] border border-[#E5E7EB] placeholder-[#94A3B8] text-[#1A1C1E] rounded-2xl focus:outline-none focus:border-[#064E3B] focus:ring-1 focus:ring-[#064E3B] transition-all font-medium"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="pt-4">
                            <button
                                type="submit"
                                className="w-full flex justify-center items-center py-5 px-4 bg-[#064E3B] text-white text-xs uppercase tracking-[0.2em] font-black rounded-2xl hover:bg-[#043327] shadow-xl shadow-[#064E3B]/20 transition-all active:scale-95 group"
                            >
                                Verificar Credenciales
                                <svg className="w-4 h-4 ml-3 transition-transform group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                                </svg>
                            </button>
                        </div>
                    </form>
                    
                    <div className="mt-8 text-center">
                        <Link href="/register" className="text-[10px] uppercase tracking-[0.2em] font-black text-[#64748B] hover:text-[#064E3B] transition-colors inline-flex items-center gap-2">
                            <span>¿No tienes cuenta?</span>
                            <span className="text-[#064E3B] border-b-2 border-[#FFD700]">Solicitar Membresía</span>
                        </Link>
                    </div>
                </div>

                <p className="mt-12 text-center text-[#94A3B8] text-[9px] uppercase tracking-[0.4em] font-medium">
                    Sistemas de Inversión ValueBet AI &copy; 2026
                </p>
            </div>
        </div>
    );
}
