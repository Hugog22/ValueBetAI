'use client';

import { useEffect } from 'react';

interface AnalysisModalProps {
  homeTeam: string;
  awayTeam: string;
  justification: string;
  onClose: () => void;
}

import RichText from '@/components/RichText';

/** Splits the justification into logical paragraphs for better readability */
function buildParagraphs(text: string): string[] {
  // Split at sentence-ending punctuation followed by transitional phrases
  return text
    .split(/(?<=[.!?])\s+(?=En |Al |Se |A esto|Con un )/)
    .map(s => s.trim())
    .filter(Boolean);
}

export default function AnalysisModal({
  homeTeam,
  awayTeam,
  justification,
  onClose,
}: AnalysisModalProps) {
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);

  const paragraphs = buildParagraphs(justification);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-[#0A0F1E]/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white w-full max-w-lg rounded-[2rem] shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200 max-h-[90vh] flex flex-col">

        {/* Header */}
        <div className="p-6 border-b border-[#E5E7EB] bg-[#F8FAFC] flex-shrink-0">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-widest block mb-1">
                Análisis de Inteligencia Artificial
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

        {/* Scrollable body */}
        <div className="overflow-y-auto flex-1">

          {/* Main analysis content */}
          <div className="p-6 pt-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-[#064E3B]/10 flex items-center justify-center flex-shrink-0">
                <svg className="w-5 h-5 text-[#064E3B]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="text-sm font-bold text-[#1A1C1E]">Por qué el modelo predice esto</h3>
            </div>

            <div className="bg-[#F8FAFC] rounded-xl p-5 border border-[#E5E7EB] space-y-3">
              {paragraphs.length > 1 ? (
                paragraphs.map((para, i) => (
                  <p key={i} className="text-[#475569] text-sm leading-relaxed">
                    <RichText text={para} />
                  </p>
                ))
              ) : (
                <p className="text-[#475569] text-sm leading-relaxed">
                  <RichText text={justification || 'Nuestro modelo detecta una discrepancia significativa en la probabilidad real del mercado. Los datos sugieren una ventaja competitiva en esta selección específica.'} />
                </p>
              )}
            </div>

            {/* Disclaimer */}
            <p className="text-[#94A3B8] text-[11px] mt-4 text-center leading-relaxed">
              Predicción generada por modelo de IA. Las apuestas implican riesgo — apuesta con responsabilidad.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
