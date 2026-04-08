/**
 * MatchesDashboard.tsx
 * --------------------
 * Client Component — owns all interactive state (filters, bet modal, bankroll).
 * Receives `initialMatches`, `initialParlay`, `initialBoosts` from the Server
 * Component as pre-fetched props (ISR data), so the page renders instantly.
 *
 * Bankroll is still fetched client-side after mount (requires the JWT token
 * from local storage via AuthContext which is unavailable on the server).
 */

'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';
import FeaturedBet from '@/components/FeaturedBet';
import CategoryCard from '@/components/CategoryCard';
import BentoCard from '@/components/BentoCard';
import BetModal from '@/components/BetModal';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

// ── Types ─────────────────────────────────────────────────────────────────────

interface Risk {
  level: string;
  badge: string;
  bgClass: string;
}

interface SuperBoost {
  match: string;
  date: string;
  market: string;
  normalOdds: number;
  boostedOdds: number;
  bookmaker: string;
}

interface PickData {
  market: string;
  outcome: string;
  bookmaker_odds?: number;
  bookmakerOdds?: number;
  stake?: number;
  label: string;
  isValueBet?: boolean;
  ev?: number;
  probability?: number;
  risk?: Risk;
  bookmaker_implied_prob?: number;
}

interface Match {
  id: number;
  date: string;
  homeTeam: string;
  awayTeam: string;
  bestPick?: PickData;
  topPicks?: PickData[];
  isSteam?: boolean;
  justification?: string;
}

interface ParlayLeg extends PickData {
  homeTeam: string;
  awayTeam: string;
}

interface ParlayData {
  legs: ParlayLeg[];
  totalOdds: number;
  jointProbability: number;
}

interface Props {
  initialMatches: Match[];
  initialParlay: ParlayData | null;
  initialBoosts: SuperBoost[];
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function MatchesDashboard({ initialMatches, initialParlay, initialBoosts }: Props) {
  const { user, token } = useAuth();

  // Data state — seeded from ISR props
  const [matches]  = useState<Match[]>(initialMatches);
  const [parlay]   = useState<ParlayData | null>(initialParlay);
  const [boosts]   = useState<SuperBoost[]>(initialBoosts);

  // UI state
  const [filterRisk, setFilterRisk] = useState<string>('all');
  const [minEV,      setMinEV]      = useState<number>(0);
  const [bankroll,   setBankroll]   = useState<number>(1000);
  const [activeBet,  setActiveBet]  = useState<{
    matchId: number; homeTeam: string; awayTeam: string;
    market: string; outcome: string; label: string;
    odds: number; probability: number; ev: number;
  } | null>(null);

  // Fetch bankroll client-side (needs JWT)
  useEffect(() => {
    if (!token) return;
    fetch(`${API}/api/bankroll/stats`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(d => setBankroll(d.current_bankroll ?? 1000))
      .catch(() => { /* silently keep default */ });
  }, [token]);

  const handleSimulateBet = (matchId: number, pick: PickData, homeTeam: string, awayTeam: string) => {
    if (!token) {
      alert('Accede a tu cuenta para registrar apuestas.');
      return;
    }
    setActiveBet({
      matchId, homeTeam, awayTeam,
      market:      pick.market,
      outcome:     pick.outcome,
      label:       pick.label,
      odds:        pick.bookmaker_odds ?? pick.bookmakerOdds ?? 1.0,
      probability: pick.probability ?? 0,
      ev:          pick.ev ?? 0,
    });
  };

  const filteredMatches = matches.filter(m => {
    const riskLevel = m.bestPick?.risk?.level || 'N/D';
    const matchesRisk = filterRisk === 'all' || riskLevel === filterRisk;
    const matchesEV   = (m.bestPick?.ev || 0) >= minEV;
    return matchesRisk && matchesEV;
  });

  const featuredMatch = matches.find(m => m.bestPick?.isValueBet) || matches[0];

  // Tailwind dynamic class safelist (prevents purging)
  const _safelist = 'bg-green-600 bg-yellow-400 bg-orange-500 bg-red-600 text-white text-black font-bold hidden';

  return (
    <>
      {/* invisible safelist div */}
      <div className={_safelist} aria-hidden />

      {/* ── HERO / FEATURED ─────────────────────────────────────────────── */}
      <section className="mb-20">
        {featuredMatch && (
          <FeaturedBet
            homeTeam={featuredMatch.homeTeam}
            awayTeam={featuredMatch.awayTeam}
            pick={featuredMatch.bestPick?.label || 'Sin selección'}
            odds={featuredMatch.bestPick?.bookmaker_odds || featuredMatch.bestPick?.bookmakerOdds || 1.0}
            aiProb={(featuredMatch.bestPick?.probability || 0) * 100}
            bookieProb={(featuredMatch.bestPick?.bookmaker_implied_prob || 0) * 100}
            risk={featuredMatch.bestPick?.risk}
            date={new Date(featuredMatch.date).toLocaleDateString('es-ES', {
              day: 'numeric', month: 'long', year: 'numeric',
              hour: '2-digit', minute: '2-digit',
            })}
            justification={featuredMatch.justification || ''}
            onAction={() => handleSimulateBet(featuredMatch.id, featuredMatch.bestPick!, featuredMatch.homeTeam, featuredMatch.awayTeam)}
          />
        )}
      </section>

      {/* ── COMBINADIA (AI PARLAY) ──────────────────────────────────────── */}
      {parlay && parlay.legs.length > 0 && (
        <section className="mb-20">
          <div className="flex items-center gap-3 mb-8">
            <span className="h-px w-8 bg-[#064E3B]" />
            <h2 className="text-3xl font-editorial font-bold text-[#1A1C1E]">
              Combinad<span className="text-[#064E3B]">IA</span>
            </h2>
          </div>
          <BentoCard className="bg-gradient-to-br from-[#064E3B] to-[#043327] text-white border-none shadow-2xl relative overflow-hidden">
            <div className="relative z-10 grid grid-cols-1 lg:grid-cols-3 gap-12 items-center">
              <div className="lg:col-span-2">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {parlay.legs.map((leg, i) => (
                    <div key={i} className="bg-white/10 backdrop-blur-md p-6 rounded-2xl border border-white/10">
                      <div className="text-[10px] font-bold text-white/60 uppercase tracking-widest mb-2">
                        {leg.homeTeam} v {leg.awayTeam}
                      </div>
                      <div className="flex justify-between items-end">
                        <div>
                          <div className="text-xs font-bold text-[#FFD700] mb-1">{leg.market}</div>
                          <div className="text-lg font-editorial font-bold">{leg.label}</div>
                        </div>
                        <div className="text-xl font-black text-white/90">{leg.bookmakerOdds?.toFixed(2)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="text-center lg:text-right flex flex-col items-center lg:items-end justify-center">
                <div className="text-[10px] font-bold text-white/60 uppercase tracking-widest mb-2">Cuota Total Combinada</div>
                <div className="text-7xl font-editorial font-bold text-[#FFD700] mb-4">{parlay.totalOdds.toFixed(2)}</div>
                <div className="bg-white/20 text-xs font-bold px-6 py-2 rounded-full mb-8">
                  Probabilidad IA: <span className="text-[#FFD700]">{parlay.jointProbability.toFixed(1)}%</span>
                </div>
                <button className="bg-[#FFD700] text-[#1A1C1E] font-black px-10 py-4 rounded-full hover:scale-105 transition-transform active:scale-95 shadow-xl shadow-black/20">
                  Sellar CombinadIA
                </button>
              </div>
            </div>
            <div className="absolute -right-20 -bottom-20 w-80 h-80 bg-white/5 rounded-full blur-3xl" />
          </BentoCard>
        </section>
      )}

      {/* ── SUPERAUMENTOS ───────────────────────────────────────────────── */}
      {boosts.length > 0 && (
        <section className="mb-20">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-3xl font-editorial font-bold text-[#1A1C1E]">Superaumentos</h2>
            <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-widest">Exclusivo Premium</span>
          </div>
          <div className="flex gap-6 overflow-x-auto pb-6 -mx-4 px-4 scrollbar-hide">
            {boosts.map((boost, i) => (
              <div key={i} className="min-w-[300px] bg-white p-8 rounded-[2rem] border border-[#E5E7EB] shadow-sm hover:shadow-xl transition-all border-t-4 border-t-[#FFD700]">
                <div className="text-[10px] font-bold text-[#64748B] uppercase tracking-widest mb-4">{boost.match}</div>
                <div className="text-sm font-bold text-[#1A1C1E] mb-1">{boost.market}</div>
                <div className="flex items-center gap-4 mt-6">
                  <div className="text-sm text-[#64748B] line-through">{boost.normalOdds.toFixed(2)}</div>
                  <div className="text-3xl font-editorial font-bold text-[#064E3B]">{boost.boostedOdds.toFixed(2)}</div>
                  <div className="ml-auto bg-[#064E3B] text-white p-2 rounded-lg">
                    <span className="text-[8px] font-bold block leading-none">{boost.bookmaker}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── EXPLORAR MERCADOS ────────────────────────────────────────────── */}
      <section className="mb-20">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-3xl font-editorial font-bold text-[#1A1C1E]">Explorar Mercados</h2>
          <Link href="#" className="text-sm font-bold text-[#1A1C1E] underline decoration-2 underline-offset-4 decoration-[#FFD700] hover:text-[#064E3B] transition-colors">
            Ver todo
          </Link>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          <CategoryCard title="La Liga"        subtitle="España"     active image="https://images.unsplash.com/photo-1574629810360-7efbbe195018?q=80&w=400&h=400&auto=format&fit=crop" />
          <CategoryCard title="Premier League" subtitle="Inglaterra"        image="https://images.unsplash.com/photo-1543351611-58f69d7c1781?q=80&w=400&h=400&auto=format&fit=crop" />
          <CategoryCard title="Champions"      subtitle="Europa"            image="https://images.unsplash.com/photo-1518063319789-7217e6706b04?q=80&w=400&h=400&auto=format&fit=crop" />
          <CategoryCard title="NBA"            subtitle="EUA"               image="https://images.unsplash.com/photo-1546519638-68e109498ffc?q=80&w=400&h=400&auto=format&fit=crop" />
        </div>
      </section>

      {/* ── RADAR DE VALOR ───────────────────────────────────────────────── */}
      <section>
        <div className="flex flex-col md:flex-row items-center justify-between mb-12 border-b border-[#E5E7EB] pb-6">
          <h2 className="text-3xl font-editorial font-bold text-[#1A1C1E]">Radar de Valor</h2>
          <div className="flex items-center gap-6 mt-6 md:mt-0">
            <div className="flex items-center gap-3">
              <span className="text-[10px] uppercase font-bold text-[#64748B] tracking-widest">Riesgo</span>
              <select
                id="filter-risk"
                value={filterRisk}
                onChange={e => setFilterRisk(e.target.value)}
                className="bg-white border border-[#E5E7EB] text-[#1A1C1E] font-bold rounded-full px-4 py-2 outline-none focus:border-[#064E3B] text-xs"
              >
                <option value="all">TODOS</option>
                <option value="BAJO">BAJO</option>
                <option value="MEDIO">MEDIO</option>
                <option value="ALTO">ALTO</option>
                <option value="LOTERÍA">LOTERÍA</option>
              </select>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-[10px] uppercase font-bold text-[#64748B] tracking-widest">Min EV</span>
              <input
                id="filter-min-ev"
                type="number"
                value={minEV}
                onChange={e => setMinEV(Number(e.target.value))}
                className="bg-white border border-[#E5E7EB] text-[#064E3B] font-black rounded-full px-4 py-2 outline-none focus:border-[#064E3B] text-xs w-16 text-center"
              />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {filteredMatches.map(match => (
            <BentoCard key={match.id} className="flex flex-col">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-widest block mb-1">
                    {new Date(match.date).toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                  </span>
                  <h3 className="text-xl font-editorial font-bold text-[#1A1C1E]">{match.homeTeam} v {match.awayTeam}</h3>
                </div>
                {match.bestPick?.risk && (
                  <div className={`${match.bestPick.risk.bgClass} px-3 py-1 rounded-lg text-[8px] font-bold uppercase tracking-widest`}>
                    {match.bestPick.risk.level}
                  </div>
                )}
                {match.isSteam && (
                  <div className="bg-[#064E3B]/10 p-1.5 rounded-full" title="Line Movement">
                    <svg className="w-3 h-3 text-[#064E3B]" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M12.395 2.553a1 1 0 00-1.450 1.348L13.143 6H3a1 1 0 100 2h10.143l-2.198 2.099a1 1 0 101.314 1.503l4-3.816a1 1 0 000-1.503l-4-3.816s.001 0 0 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                )}
              </div>

              <div className="mt-auto space-y-4">
                {(match.topPicks || (match.bestPick ? [match.bestPick] : [])).slice(0, 1).map((pick, pi) => (
                  <div key={pi} className="group">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-widest">{pick.market}</span>
                      <span className="text-xs font-bold text-[#064E3B]">
                        AI {((pick.probability ?? 0) * 100).toFixed(0)}% vs Casa {((pick.bookmaker_implied_prob ?? 0) * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <div className="text-lg font-editorial font-bold text-[#1A1C1E]">{pick.label}</div>
                      <button
                        onClick={() => handleSimulateBet(match.id, pick, match.homeTeam, match.awayTeam)}
                        className="bg-[#F1F3F5] hover:bg-[#064E3B] hover:text-white text-[#1A1C1E] font-black px-4 py-2 rounded-xl transition-all active:scale-95 min-w-[60px]"
                      >
                        {(pick.bookmaker_odds || pick.bookmakerOdds || 1.0).toFixed(2)}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </BentoCard>
          ))}
        </div>
      </section>

      {/* ── BET MODAL ────────────────────────────────────────────────────── */}
      {activeBet && token && (
        <BetModal
          {...activeBet}
          token={token}
          currentBankroll={bankroll}
          onClose={() => setActiveBet(null)}
          onSuccess={(newBankroll) => {
            setBankroll(newBankroll);
            setActiveBet(null);
            alert(`✅ Apuesta registrada. Bankroll actualizado: ${newBankroll.toFixed(2)} €`);
          }}
        />
      )}
    </>
  );
}
