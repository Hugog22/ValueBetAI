'use client';

import { useState, useEffect } from 'react';

interface BetModalProps {
  matchId: number;
  homeTeam: string;
  awayTeam: string;
  market: string;
  outcome: string;
  label: string;
  odds: number;
  probability: number;
  ev: number;
  token: string;
  currentBankroll: number;
  onClose: () => void;
  onSuccess: (newBankroll: number) => void;
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export default function BetModal({
  matchId, homeTeam, awayTeam, market, outcome, label,
  odds, probability, ev, token, currentBankroll, onClose, onSuccess
}: BetModalProps) {
  const [stake, setStake] = useState<string>('10');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const stakeNum = parseFloat(stake) || 0;
  const potentialReturn = stakeNum * odds;
  const potentialProfit = potentialReturn - stakeNum;
  const remainingBankroll = currentBankroll - stakeNum;

  // Quick stake buttons
  const quickStakes = [5, 10, 25, 50];

  // Prevent background scroll
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);

  const handleSubmit = async () => {
    if (stakeNum <= 0) { setError('Introduce un stake mayor que 0'); return; }
    if (stakeNum > currentBankroll) { setError(`Saldo insuficiente. Disponible: ${currentBankroll.toFixed(2)} €`); return; }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API}/api/bets`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          match_id: matchId,
          bookmaker: 'Bet365',
          market,
          selection: outcome,
          odds_taken: odds,
          stake: stakeNum
        })
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || 'Error al registrar la apuesta');
        return;
      }

      onSuccess(data.new_bankroll ?? (currentBankroll - stakeNum));
    } catch {
      setError('Error de red. Inténtalo de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />

      <div
        className="relative bg-white rounded-[2rem] shadow-[0_40px_80px_rgba(0,0,0,0.15)] w-full max-w-md overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-[#1A1C1E] px-8 py-6">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[9px] font-bold uppercase tracking-[0.3em] text-white/50">Confirmar Posición</span>
            <button onClick={onClose} className="text-white/40 hover:text-white transition-colors text-xl leading-none">×</button>
          </div>
          <div className="text-xl font-editorial font-bold text-white">
            {homeTeam} <span className="text-white/40 font-sans text-sm font-normal">vs</span> {awayTeam}
          </div>
        </div>

        <div className="px-8 py-6 space-y-6">
          {/* Bet summary */}
          <div className="bg-[#F8F9FA] rounded-2xl p-5 space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-xs text-[#64748B] font-bold uppercase tracking-widest">Mercado</span>
              <span className="text-sm font-bold text-[#1A1C1E]">{market}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-[#64748B] font-bold uppercase tracking-widest">Selección</span>
              <span className="text-sm font-editorial font-bold text-[#064E3B]">{label}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-[#64748B] font-bold uppercase tracking-widest">Cuota</span>
              <span className="text-2xl font-editorial font-bold text-[#1A1C1E]">{odds.toFixed(2)}</span>
            </div>
            <div className="flex justify-between items-center border-t border-[#E5E7EB] pt-3">
              <span className="text-xs text-[#64748B] font-bold uppercase tracking-widest">Prob. IA / EV</span>
              <span className="text-xs font-bold text-[#064E3B]">
                {(probability * 100).toFixed(1)}% · EV +{(ev * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          {/* Bankroll display */}
          <div className="flex items-center justify-between text-sm">
            <span className="text-[#64748B] font-medium">Bankroll disponible</span>
            <span className="font-editorial font-bold text-[#064E3B] text-lg">{currentBankroll.toFixed(2)} €</span>
          </div>

          {/* Stake input */}
          <div>
            <label className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#64748B] block mb-3">
              Cantidad a apostar (€)
            </label>
            <div className="relative">
              <input
                type="number"
                min="1"
                max={currentBankroll}
                step="1"
                value={stake}
                onChange={e => { setStake(e.target.value); setError(null); }}
                className="w-full border-2 border-[#E5E7EB] focus:border-[#064E3B] rounded-xl px-5 py-4 text-2xl font-editorial font-bold text-[#1A1C1E] outline-none transition-colors pr-14"
              />
              <span className="absolute right-5 top-1/2 -translate-y-1/2 text-[#64748B] font-bold">€</span>
            </div>

            {/* Quick stake buttons */}
            <div className="flex gap-2 mt-3">
              {quickStakes.map(q => (
                <button
                  key={q}
                  onClick={() => { setStake(String(q)); setError(null); }}
                  className="flex-1 py-2 rounded-xl text-xs font-bold border border-[#E5E7EB] hover:border-[#064E3B] hover:text-[#064E3B] transition-all"
                >
                  {q} €
                </button>
              ))}
              <button
                onClick={() => { setStake(String(Math.floor(currentBankroll))); setError(null); }}
                className="flex-1 py-2 rounded-xl text-xs font-bold border border-[#E5E7EB] hover:border-red-400 hover:text-red-500 transition-all"
              >
                MAX
              </button>
            </div>
          </div>

          {/* Return preview */}
          {stakeNum > 0 && stakeNum <= currentBankroll && (
            <div className="bg-[#064E3B]/5 border border-[#064E3B]/20 rounded-2xl p-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-[#64748B]">Retorno potencial</span>
                <span className="font-editorial font-bold text-[#064E3B]">+{potentialReturn.toFixed(2)} €</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[#64748B]">Beneficio neto</span>
                <span className="font-bold text-[#064E3B]">+{potentialProfit.toFixed(2)} €</span>
              </div>
              <div className="flex justify-between text-sm border-t border-[#064E3B]/10 pt-2">
                <span className="text-[#64748B]">Bankroll tras apuesta</span>
                <span className={`font-bold ${remainingBankroll < 20 ? 'text-red-500' : 'text-[#1A1C1E]'}`}>
                  {remainingBankroll.toFixed(2)} €
                </span>
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600 font-medium">
              {error}
            </div>
          )}

          {/* CTA */}
          <button
            onClick={handleSubmit}
            disabled={loading || stakeNum <= 0 || stakeNum > currentBankroll}
            className="w-full bg-[#064E3B] text-white py-4 rounded-xl font-bold text-sm tracking-wide hover:bg-[#065f46] transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Confirmando...
              </>
            ) : (
              <>Confirmar Apuesta · {stakeNum > 0 ? `${stakeNum} €` : '—'}</>
            )}
          </button>

          <p className="text-center text-[10px] text-[#94a3b8] leading-relaxed">
            Esta es una simulación virtual. El stake se descuenta de tu bankroll inmediatamente.<br />
            Los resultados se liquidan automáticamente cada martes.
          </p>
        </div>
      </div>
    </div>
  );
}
