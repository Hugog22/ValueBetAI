'use client';

import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="fixed top-0 w-full z-50 glass-light">
      <div className="max-w-7xl mx-auto px-8 h-20 flex justify-between items-center transition-all">
        {/* Logo and Nav links */}
        <div className="flex items-center gap-10">
          <Link href="/" className="flex items-center gap-2">
            <div className="h-10 w-10 bg-[#FFD700] flex items-center justify-center rounded-lg shadow-sm">
              <span className="text-[#1A1C1E] font-black text-xs leading-none">BET<br/>AI</span>
            </div>
            <span className="text-xl font-editorial font-bold tracking-tight text-[#1A1C1E]">
              ValueBet <span className="opacity-50">AI</span>
            </span>
          </Link>
          <nav className="hidden md:flex items-center gap-8 text-sm font-semibold text-[#1A1C1E]/60">
            <Link href="/" className="text-[#1A1C1E] underline decoration-2 underline-offset-8 decoration-[#FFD700]">Inicio</Link>
            <Link href="#radar-de-valor" className="hover:text-[#1A1C1E] transition-colors">Análisis</Link>
            <Link href="#explorar-mercados" className="hover:text-[#1A1C1E] transition-colors">Mercados</Link>
          </nav>
        </div>

        {/* Search and Auth */}
        <div className="flex items-center gap-6 flex-1 max-w-md justify-end">
          {user ? (
            <div className="flex items-center gap-4">
              <button 
                onClick={logout}
                className="text-xs font-bold text-[#1A1C1E]/60 hover:text-red-600 transition-colors uppercase tracking-widest"
              >
                Salir
              </button>
              <Link 
                href="/bankroll"
                className="bg-[#1A1C1E] text-white px-6 py-2.5 rounded-full text-sm font-bold tracking-tight hover:bg-[#064E3B] transition-all"
              >
                Mi Portafolio
              </Link>
            </div>
          ) : (
            <Link 
              href="/login"
              className="bg-[#1A1C1E] text-white px-8 py-3 rounded-full text-sm font-bold tracking-tight hover:bg-[#064E3B] transition-all flex items-center gap-2"
            >
              <span>Acceder</span>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}

