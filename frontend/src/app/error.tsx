'use client';

import { useEffect } from 'react';
import Link from 'next/link';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#FCF9F1] px-4 text-center">
      <div className="bg-white p-10 rounded-[2.5rem] border border-[#E5E7EB] shadow-[0_20px_50px_rgba(0,0,0,0.04)] max-w-md w-full">
        <div className="w-16 h-16 bg-[#FEE2E2] rounded-full flex items-center justify-center mx-auto mb-6 text-red-600">
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
             <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h2 className="text-2xl font-editorial font-bold text-[#1A1C1E] mb-4">Algo ha ido mal</h2>
        <p className="text-[#64748B] mb-8 text-sm leading-relaxed">
          Ocurrió un error inesperado al renderizar esta página.
        </p>
        <button
          onClick={() => reset()}
          className="w-full flex justify-center items-center py-4 px-4 bg-[#064E3B] text-white text-xs uppercase tracking-[0.2em] font-black rounded-2xl hover:bg-[#043327] shadow-xl shadow-[#064E3B]/20 transition-all active:scale-95 group mb-4"
        >
          Intentar de nuevo
        </button>
        <Link href="/" className="text-[10px] uppercase tracking-[0.2em] font-black text-[#64748B] hover:text-[#064E3B] transition-colors">
          Volver al Inicio
        </Link>
      </div>
    </div>
  );
}
