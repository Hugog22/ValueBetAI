'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useAuth } from '@/context/AuthContext';

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="fixed top-0 w-full z-50 glass-light overflow-x-auto scrollbar-hide">
      <div className="max-w-7xl mx-auto px-4 md:px-8 h-20 flex justify-between items-center transition-all min-w-max md:min-w-0 gap-6 md:gap-0">
        {/* Logo and Nav links */}
        <div className="flex items-center gap-6 md:gap-10">
          <Link href="/" className="flex items-center shrink-0"><Image src="/logo.png" alt="QuantStake Logo" width={160} height={40} className="h-8 w-auto object-contain" priority /></Link>
          <nav className="flex items-center gap-4 md:gap-8 text-xs md:text-sm font-semibold text-[#1A1C1E]/60 shrink-0">
            <Link href="/" className="text-[#1A1C1E] underline decoration-2 underline-offset-8 decoration-[#FFD700]">Inicio</Link>
            <Link href="#radar-de-valor" className="hover:text-[#1A1C1E] transition-colors">Análisis</Link>
            <Link href="#explorar-mercados" className="hover:text-[#1A1C1E] transition-colors">Mercados</Link>
          </nav>
        </div>

        {/* Search and Auth */}
        <div className="flex items-center gap-4 md:gap-6 flex-1 justify-end shrink-0 pr-4 md:pr-0">
          {user ? (
            <div className="flex items-center gap-4">
              <button 
                onClick={logout}
                className="text-[10px] md:text-xs font-bold text-[#1A1C1E]/60 hover:text-red-600 transition-colors uppercase tracking-widest"
              >
                Salir
              </button>
              <Link 
                href="/bankroll"
                className="bg-[#1A1C1E] text-white px-4 md:px-6 py-2 md:py-2.5 rounded-full text-[11px] md:text-sm font-bold tracking-tight hover:bg-[#064E3B] transition-all whitespace-nowrap"
              >
                Mi Perfil Digital
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

