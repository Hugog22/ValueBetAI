'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

export default function CookieBanner() {
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        const consent = localStorage.getItem('cookie_consent');
        if (!consent) {
            setIsVisible(true);
        }
    }, []);

    const acceptCookies = () => {
        localStorage.setItem('cookie_consent', 'true');
        setIsVisible(false);
    };

    if (!isVisible) return null;

    return (
        <div className="fixed bottom-0 left-0 w-full z-[100] p-4 md:p-6 pointer-events-none">
            <div className="max-w-4xl mx-auto bg-[#051209] text-[#94a3b8] p-6 rounded-2xl shadow-[0_0_50px_rgba(0,0,0,0.5)] border border-white/10 flex flex-col md:flex-row items-center justify-between gap-6 pointer-events-auto">
                <div className="text-sm">
                    Utilizamos tecnologías como cookies y almacenamiento local estrictamente necesarias para el funcionamiento de la plataforma y para mantener tu sesión segura. 
                    No utilizamos cookies para rastreo de terceros ni fines publicitarios.{' '}
                    <Link href="/cookies" className="text-[#C0FF00] hover:underline whitespace-nowrap font-medium">
                        Ver Política de Cookies
                    </Link>
                </div>
                <div className="shrink-0 w-full md:w-auto flex gap-4">
                    <button 
                        onClick={acceptCookies}
                        className="w-full md:w-auto px-6 py-2.5 bg-[#C0FF00] text-[#051209] rounded-xl font-bold text-sm hover:bg-[#a3d900] transition-colors shadow-[0_0_20px_rgba(192,255,0,0.2)]"
                    >
                        Aceptar y cerrar
                    </button>
                </div>
            </div>
        </div>
    );
}
