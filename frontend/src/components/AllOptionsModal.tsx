'use client';

import { useEffect, useState } from 'react';

interface PickData {
  market: string;
  outcome: string;
  bookmaker_odds?: number;
  bookmakerOdds?: number;
  label: string;
  isValueBet?: boolean;
  is_value?: boolean;
  probability?: number;
  bookmaker_implied_prob?: number;
}

interface AllOptionsModalProps {
  homeTeam: string;
  awayTeam: string;
  allCandidates: PickData[];
  onClose: () => void;
  onSimulateBet: (candidate: PickData) => void;
}

export default function AllOptionsModal({
  homeTeam,
  awayTeam,
  allCandidates,
  onClose,
  onSimulateBet,
}: AllOptionsModalProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, []);

  if (!mounted) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-[#0A0F1E]/80 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-white rounded-3xl shadow-2xl w-full max-w-4xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="bg-[#0A0F1E] text-white p-6 md:p-8 flex items-center justify-between">
          <div>
            <div className="text-[10px] font-bold text-white/60 uppercase tracking-widest mb-2">
              Todas las opciones evaluadas
            </div>
            <h2 className="text-2xl md:text-3xl font-editorial font-bold">
              {homeTeam} vs {awayTeam}
            </h2>
          </div>
          <button 
            onClick={onClose}
            className="p-2 bg-white/10 hover:bg-white/20 rounded-full transition-colors text-white"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Info Banner */}
        <div className="bg-amber-50 border-b border-amber-100 p-4 px-6 md:px-8">
          <p className="text-amber-800 text-sm font-medium flex items-center gap-2">
            <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <strong>Importante:</strong> Todas las cuotas que se muestran son cuotas medias extraídas de múltiples casas de apuestas.
          </p>
        </div>

        {/* Content */}
        <div className="p-6 md:p-8 max-h-[60vh] overflow-y-auto">
          {allCandidates.length === 0 ? (
            <div className="text-center py-12 text-[#64748B]">
              No hay opciones disponibles para este partido.
            </div>
          ) : (
            <div className="grid gap-4">
              {allCandidates.map((candidate, index) => {
                const odds = candidate.bookmaker_odds ?? candidate.bookmakerOdds ?? 1.0;
                const bookieProb = (candidate.bookmaker_implied_prob ?? 0) * 100;
                const aiProb = (candidate.probability ?? 0) * 100;
                const isValue = candidate.isValueBet || candidate.is_value;
                
                return (
                  <div 
                    key={index} 
                    className={`border rounded-2xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 transition-colors ${
                      isValue 
                        ? 'border-[#064E3B] bg-[#064E3B]/5' 
                        : 'border-[#E5E7EB] hover:border-[#CBD5E1]'
                    }`}
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-widest">
                          {candidate.market}
                        </span>
                        {isValue && (
                          <span className="bg-[#064E3B] text-white px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider">
                            Value Bet
                          </span>
                        )}
                        <button
                          onClick={() => onSimulateBet(candidate)}
                          className="bg-[#1A1C1E] hover:bg-[#064E3B] text-white px-3 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider transition-colors"
                        >
                          Apostar
                        </button>
                      </div>
                      <h3 className="text-lg font-editorial font-bold text-[#1A1C1E]">
                        {candidate.label}
                      </h3>
                    </div>

                    <div className="grid grid-cols-2 md:flex md:items-center gap-6">
                      <div className="text-left md:text-right">
                        <div className="text-[10px] font-bold text-[#64748B] uppercase tracking-widest mb-1">
                          Prob. Media Casa
                        </div>
                        <div className="font-bold text-[#1A1C1E]">
                          {bookieProb.toFixed(1)}%
                        </div>
                      </div>
                      
                      <div className="text-left md:text-right">
                        <div className="text-[10px] font-bold text-[#64748B] uppercase tracking-widest mb-1">
                          Prob. IA
                        </div>
                        <div className={`font-bold ${candidate.isValueBet ? 'text-[#064E3B]' : 'text-[#1A1C1E]'}`}>
                          {aiProb.toFixed(1)}%
                        </div>
                      </div>

                      <div className="col-span-2 md:col-span-1 text-right mt-2 md:mt-0">
                        <div className="bg-[#1A1C1E] text-white px-5 py-3 rounded-xl font-black text-center min-w-[80px]">
                          {odds.toFixed(2)}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
        
        {/* Footer */}
        <div className="bg-gray-50 border-t border-gray-100 p-6 flex justify-end">
          <button 
            onClick={onClose}
            className="px-6 py-2.5 bg-white border border-[#E5E7EB] text-[#1A1C1E] font-bold rounded-xl hover:bg-gray-50 transition-colors"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
