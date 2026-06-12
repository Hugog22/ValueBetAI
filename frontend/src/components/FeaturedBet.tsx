'use client';

import { useState } from 'react';
import Image from 'next/image';

interface FeaturedBetProps {
  homeTeam: string;
  awayTeam: string;
  pick: string;
  odds: number;
  date: string;
  justification: string;
  onAction: () => void;
  imagePath?: string;
  aiProb?: number;
  bookieProb?: number;
  risk?: {
    level: string;
    badge: string;
    bgClass: string;
  };
  allBookmakers?: { title: string; home_odds: number; draw_odds: number; away_odds: number }[];
}

export default function FeaturedBet({
  homeTeam,
  awayTeam,
  pick,
  odds,
  date,
  justification,
  onAction,
  risk,
  aiProb = 0,
  bookieProb = 0,
  imagePath = '/featured_bet_placeholder.png',
  allBookmakers = []
}: FeaturedBetProps) {
  const [showBookies, setShowBookies] = useState(false);
  return (
    <div className="bento-card grid grid-cols-1 lg:grid-cols-2 min-h-[500px]">
      {/* Image Side */}
      <div className="relative h-[300px] lg:h-full overflow-hidden">
        <Image 
          src={imagePath} 
          alt="Sports analysis" 
          fill 
          className="object-cover transition-transform duration-700 hover:scale-105"
          priority
        />
        <div className="absolute top-8 left-8 flex gap-2">
          <span className="bg-[#064E3B] text-white px-4 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-widest">
            Best Pick
          </span>
          <span className="bg-[#B45309] text-white px-4 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-widest">
            AI {aiProb.toFixed(0)}% vs Media {bookieProb.toFixed(0)}%
          </span>
          {risk && (
            <span className={`${risk.bgClass} px-4 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-widest shadow-lg shadow-black/5`}>
              Riesgo {risk.level}
            </span>
          )}
        </div>
      </div>

      {/* Content Side */}
      <div className="p-10 lg:p-16 flex flex-col justify-center">
        <div className="flex items-center gap-2 text-xs font-bold text-[#64748B] uppercase tracking-[0.2em] mb-6">
          <span>{date}</span>
          <span className="w-1 h-1 bg-[#D1D5DB] rounded-full"></span>
          <span>Analizado por IA</span>
        </div>

        <h1 className="text-4xl lg:text-5xl font-editorial font-bold text-[#1A1C1E] leading-[1.1] mb-6">
          {homeTeam} <span className="text-[#64748B] italic">contra</span> {awayTeam}
        </h1>

        <p className="text-[#64748B] text-lg leading-relaxed mb-10 font-medium">
          {justification || "Nuestro modelo detecta una discrepancia significativa en la probabilidad real del mercado. Los datos sugieren una ventaja competitiva en esta selección específica."}
        </p>

        <div className="flex flex-col sm:flex-row items-center gap-6 pt-6 border-t border-[#E5E7EB]">
          <div className="flex-1">
            <span className="block text-[10px] font-bold text-[#64748B] uppercase tracking-widest mb-1">Mercado sugerido</span>
            <span className="text-2xl font-editorial font-bold text-[#1A1C1E]">{pick}</span>
          </div>
          
          <div className="relative">
            <button 
              onClick={onAction}
              className="btn-premium group"
            >
              Asegurar cuota media {odds.toFixed(2)}
              <svg className="w-4 h-4 ml-3 transition-transform group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
            {allBookmakers && allBookmakers.length > 0 && (
              <button 
                onClick={() => setShowBookies(!showBookies)}
                className="absolute -bottom-8 right-0 text-[10px] font-bold text-[#64748B] uppercase hover:text-[#064E3B] transition-colors flex items-center gap-1"
              >
                Ver cuotas detalladas 
                <svg className={`w-3 h-3 transition-transform ${showBookies ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            )}
            
            {showBookies && allBookmakers && allBookmakers.length > 0 && (
              <div className="absolute top-full right-0 mt-4 bg-white border border-[#E5E7EB] rounded-xl shadow-xl z-10 w-64 overflow-hidden">
                <div className="bg-[#F8FAFC] px-4 py-2 border-b border-[#E5E7EB] flex justify-between items-center text-[10px] font-bold text-[#64748B] uppercase tracking-widest">
                  <span>Casa de apuestas</span>
                  <span>Cuota H2H</span>
                </div>
                <div className="max-h-60 overflow-y-auto">
                  {allBookmakers.map((b, i) => (
                    <div key={i} className="px-4 py-3 border-b border-[#E5E7EB] last:border-0 hover:bg-[#F8FAFC] transition-colors flex justify-between items-center">
                      <span className="text-sm font-bold text-[#1A1C1E]">{b.title}</span>
                      <div className="flex gap-2 text-xs">
                        <span className="bg-[#E2E8F0] px-2 py-0.5 rounded font-bold text-[#475569]">{b.home_odds.toFixed(2)}</span>
                        <span className="bg-[#E2E8F0] px-2 py-0.5 rounded font-bold text-[#475569]">{b.draw_odds.toFixed(2)}</span>
                        <span className="bg-[#E2E8F0] px-2 py-0.5 rounded font-bold text-[#475569]">{b.away_odds.toFixed(2)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
