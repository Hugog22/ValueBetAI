'use client';

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
  imagePath = '/featured_bet_placeholder.png'
}: FeaturedBetProps) {
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
            AI {aiProb.toFixed(0)}% vs Casa {bookieProb.toFixed(0)}%
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
          
          <button 
            onClick={onAction}
            className="btn-premium group"
          >
            Asegurar cuota {odds.toFixed(2)}
            <svg className="w-4 h-4 ml-3 transition-transform group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
