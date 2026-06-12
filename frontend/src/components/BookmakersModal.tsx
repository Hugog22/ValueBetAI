'use client';

import { useEffect } from 'react';

interface BookmakerOdds {
  title: string;
  home_odds: number;
  draw_odds: number;
  away_odds: number;
}

interface BookmakersModalProps {
  homeTeam: string;
  awayTeam: string;
  bookmakers: BookmakerOdds[];
  onClose: () => void;
}

export default function BookmakersModal({
  homeTeam,
  awayTeam,
  bookmakers,
  onClose
}: BookmakersModalProps) {
  // Prevent background scroll
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-[#0A0F1E]/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white w-full max-w-md rounded-[2rem] shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="p-6 border-b border-[#E5E7EB] bg-[#F8FAFC]">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-widest block mb-1">
                Comparativa de Cuotas H2H
              </span>
              <h2 className="text-xl font-editorial font-bold text-[#1A1C1E] leading-tight">
                {homeTeam} <span className="text-[#64748B] italic font-normal text-lg">vs</span> {awayTeam}
              </h2>
            </div>
            <button 
              onClick={onClose}
              className="p-2 text-[#94A3B8] hover:text-[#1A1C1E] hover:bg-[#F1F3F5] rounded-full transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 max-h-[60vh] overflow-y-auto">
          {bookmakers.length === 0 ? (
            <div className="text-center py-8 text-[#64748B]">
              No hay cuotas detalladas disponibles para este partido.
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex justify-between items-center px-2 text-[10px] font-bold text-[#64748B] uppercase tracking-widest mb-2">
                <span>Casa de apuestas</span>
                <div className="flex gap-4">
                  <span className="w-10 text-center">1</span>
                  <span className="w-10 text-center">X</span>
                  <span className="w-10 text-center">2</span>
                </div>
              </div>
              
              {bookmakers.map((b, i) => (
                <div key={i} className="flex justify-between items-center p-3 rounded-xl border border-[#E5E7EB] hover:border-[#CBD5E1] hover:bg-[#F8FAFC] transition-colors">
                  <span className="text-sm font-bold text-[#1A1C1E]">{b.title}</span>
                  <div className="flex gap-2">
                    <div className="w-12 py-1.5 bg-white border border-[#E5E7EB] rounded-lg text-center text-xs font-bold text-[#064E3B] shadow-sm">
                      {b.home_odds.toFixed(2)}
                    </div>
                    <div className="w-12 py-1.5 bg-white border border-[#E5E7EB] rounded-lg text-center text-xs font-bold text-[#64748B] shadow-sm">
                      {b.draw_odds.toFixed(2)}
                    </div>
                    <div className="w-12 py-1.5 bg-white border border-[#E5E7EB] rounded-lg text-center text-xs font-bold text-[#064E3B] shadow-sm">
                      {b.away_odds.toFixed(2)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
