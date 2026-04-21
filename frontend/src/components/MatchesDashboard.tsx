'use client';

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';
import FeaturedBet from '@/components/FeaturedBet';
import BentoCard from '@/components/BentoCard';
import BetModal from '@/components/BetModal';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

// ── Sport Config ─────────────────────────────────────────────────────────────

const SPORTS = [
  {
    key:      'laliga',
    label:    'La Liga',
    subtitle: 'España',
    flag:     '🇪🇸',
    image:    'https://images.unsplash.com/photo-1574629810360-7efbbe195018?q=80&w=400&h=400&auto=format&fit=crop',
  },
  {
    key:      'premier',
    label:    'Premier League',
    subtitle: 'Inglaterra',
    flag:     '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
    image:    'https://images.unsplash.com/photo-1543351611-58f69d7c1781?q=80&w=400&h=400&auto=format&fit=crop',
  },
  {
    key:      'champions',
    label:    'Champions',
    subtitle: 'Europa',
    flag:     '🏆',
    image:    'https://images.unsplash.com/photo-1518063319789-7217e6706b04?q=80&w=400&h=400&auto=format&fit=crop',
  },
  {
    key:      'nba',
    label:    'NBA',
    subtitle: 'EUA',
    flag:     '🏀',
    image:    'https://images.unsplash.com/photo-1546519638-68e109498ffc?q=80&w=400&h=400&auto=format&fit=crop',
  },
] as const;

type SportKey = typeof SPORTS[number]['key'];

// ── Types ─────────────────────────────────────────────────────────────────────

interface Risk { level: string; badge: string; bgClass: string; }

interface PickData {
  market: string; outcome: string;
  bookmaker_odds?: number; bookmakerOdds?: number;
  stake?: number; label: string;
  isValueBet?: boolean; ev?: number; probability?: number;
  risk?: Risk; bookmaker_implied_prob?: number;
}

interface Match {
  id: number; date: string;
  homeTeam: string; awayTeam: string;
  sport?: string;
  bestPick?: PickData; topPicks?: PickData[];
  isSteam?: boolean; justification?: string;
}

interface ParlayLeg extends PickData {
  homeTeam: string; awayTeam: string;
}

interface ParlayData {
  sport: string; label: string; flag: string;
  legs: ParlayLeg[]; totalOdds: number; jointProbability: number;
  message?: string;
}

interface Props {
  initialMatches: Match[];
  initialParlay: ParlayData | null;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function MatchesDashboard({ initialMatches, initialParlay }: Props) {
  const { token } = useAuth();

  // Sport selector
  const [activeSport, setActiveSport] = useState<SportKey>('laliga');
  const [sportLoading, setSportLoading] = useState(false);

  // Match data — seeded from ISR props for LaLiga
  const [matchesBySport, setMatchesBySport] = useState<Record<SportKey, Match[]>>({
    laliga:    initialMatches,
    premier:   [],
    champions: [],
    nba:       [],
  });

  // Parlays — seeded from ISR for LaLiga
  const [allParlays, setAllParlays] = useState<ParlayData[]>(
    initialParlay?.legs?.length ? [{ sport: 'laliga', label: 'La Liga', flag: '🇪🇸', ...initialParlay }] : []
  );

  // UI state
  const [filterRisk, setFilterRisk] = useState<string>('all');
  const [minEV,      setMinEV]      = useState<number>(0);
  const [bankroll,   setBankroll]   = useState<number>(1000);
  const [activeBet,  setActiveBet]  = useState<{
    matchId: number; homeTeam: string; awayTeam: string;
    market: string; outcome: string; label: string;
    odds: number; probability: number; ev: number;
  } | null>(null);

  // Fetch bankroll
  useEffect(() => {
    if (!token) return;
    fetch(`${API}/api/bankroll/stats`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(d => setBankroll(d.current_bankroll ?? 1000))
      .catch(() => {});
  }, [token]);

  // Fetch all parlays from API
  useEffect(() => {
    fetch(`${API}/api/sports/all_parlays`)
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data) && data.length > 0) setAllParlays(data);
      })
      .catch(() => {});
  }, []);

  // Fetch matches for a sport on demand
  const fetchSport = useCallback(async (sport: SportKey) => {
    if (sport === 'laliga' && matchesBySport.laliga.length > 0) return; // already loaded
    if (matchesBySport[sport].length > 0) return;

    setSportLoading(true);
    try {
      const res = await fetch(`${API}/api/matches/${sport}/jornada`);
      if (!res.ok) return;
      const data = await res.json();
      const matches: Match[] = Array.isArray(data) ? data : (data?.data ?? []);
      setMatchesBySport(prev => ({ ...prev, [sport]: matches }));
    } catch { /* silent */ }
    finally { setSportLoading(false); }
  }, [matchesBySport]);

  // Trigger fetch when sport changes
  useEffect(() => {
    fetchSport(activeSport);
  }, [activeSport, fetchSport]);

  const handleSimulateBet = (matchId: number, pick: PickData, homeTeam: string, awayTeam: string) => {
    if (!token) { alert('Accede a tu cuenta para registrar apuestas.'); return; }
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

  const activeMatches = matchesBySport[activeSport] ?? [];
  const filteredMatches = activeMatches.filter(m => {
    const riskLevel  = m.bestPick?.risk?.level || 'N/D';
    const matchesRisk = filterRisk === 'all' || riskLevel === filterRisk;
    const matchesEV   = (m.bestPick?.ev || 0) >= minEV;
    return matchesRisk && matchesEV;
  });

  const featuredMatch = activeMatches.find(m => m.bestPick?.isValueBet) || activeMatches[0];

  // Tailwind safelist
  const _safelist = 'bg-green-600 bg-yellow-400 bg-orange-500 bg-red-600 text-white text-black font-bold hidden';

  const activeSportConfig = SPORTS.find(s => s.key === activeSport)!;

  return (
    <>
      <div className={_safelist} aria-hidden />

      {/* ── HERO / FEATURED ─────────────────────────────────────────────── */}
      {featuredMatch && (
        <section className="mb-20">
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
        </section>
      )}

      {/* ── COMBINADIAS (multiple AI parlays) ───────────────────────────── */}
      {allParlays.filter(p => p.legs?.length > 0).length > 0 && (
        <section className="mb-20">
          <div className="flex items-center gap-3 mb-8">
            <span className="h-px w-8 bg-[#064E3B]" />
            <h2 className="text-3xl font-editorial font-bold text-[#1A1C1E]">
              Combinad<span className="text-[#064E3B]">IA</span>s
            </h2>
            <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-widest ml-2">
              {allParlays.filter(p => p.legs?.length > 0).length} selecciones activas
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {allParlays.filter(p => p.legs?.length > 0).map((parlay, pi) => (
              <div
                key={pi}
                className="bg-gradient-to-br from-[#064E3B] to-[#043327] text-white rounded-[2rem] shadow-xl relative overflow-hidden p-8"
              >
                {/* Sport header */}
                <div className="flex items-center gap-3 mb-6">
                  <span className="text-2xl">{parlay.flag}</span>
                  <div>
                    <div className="text-[10px] font-bold text-white/60 uppercase tracking-widest">CombinAIA</div>
                    <div className="text-lg font-editorial font-bold">{parlay.label}</div>
                  </div>
                  <div className="ml-auto text-right">
                    <div className="text-[10px] font-bold text-white/60 uppercase tracking-widest mb-1">Cuota Total</div>
                    <div className="text-3xl font-editorial font-bold text-[#FFD700]">
                      {parlay.totalOdds?.toFixed(2)}
                    </div>
                  </div>
                </div>

                {/* Legs */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
                  {(parlay.legs || []).map((leg, li) => (
                    <div key={li} className="bg-white/10 backdrop-blur-md p-4 rounded-xl border border-white/10">
                      <div className="text-[10px] font-bold text-white/60 uppercase tracking-widest mb-1 truncate">
                        {leg.homeTeam} v {leg.awayTeam}
                      </div>
                      <div className="flex justify-between items-end">
                        <div>
                          <div className="text-[10px] font-bold text-[#FFD700] mb-0.5">{leg.market}</div>
                          <div className="text-sm font-editorial font-bold">{leg.label}</div>
                        </div>
                        <div className="text-lg font-black text-white/90">{leg.bookmakerOdds?.toFixed(2)}</div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between">
                  <div className="bg-white/20 text-xs font-bold px-4 py-1.5 rounded-full">
                    Prob. IA: <span className="text-[#FFD700]">{parlay.jointProbability?.toFixed(1)}%</span>
                  </div>
                  <button
                    onClick={() => setActiveSport(parlay.sport as SportKey)}
                    className="bg-[#FFD700] text-[#1A1C1E] font-black text-xs px-5 py-2 rounded-full hover:scale-105 transition-transform active:scale-95"
                  >
                    Ver partidos →
                  </button>
                </div>

                <div className="absolute -right-16 -bottom-16 w-64 h-64 bg-white/5 rounded-full blur-3xl pointer-events-none" />
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── EXPLORAR MERCADOS — Sport Selector ───────────────────────────── */}
      <section className="mb-20">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-3xl font-editorial font-bold text-[#1A1C1E]">Explorar Mercados</h2>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {SPORTS.map(sport => {
            const isActive = activeSport === sport.key;
            const matchCount = matchesBySport[sport.key].length;
            return (
              <button
                key={sport.key}
                onClick={() => setActiveSport(sport.key)}
                className={`group text-left flex flex-col gap-3 transition-all duration-200 ${
                  isActive ? 'opacity-100' : 'opacity-60 hover:opacity-90'
                }`}
                aria-pressed={isActive}
              >
                <div className={`relative aspect-square rounded-[2rem] overflow-hidden border-2 transition-all ${
                  isActive ? 'border-[#064E3B] shadow-lg shadow-[#064E3B]/20' : 'border-transparent group-hover:border-[#E5E7EB]'
                }`}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={sport.image}
                    alt={sport.label}
                    className={`w-full h-full object-cover transition-all duration-500 group-hover:scale-110 ${
                      isActive ? 'grayscale-0' : 'grayscale group-hover:grayscale-0'
                    }`}
                  />
                  {isActive && (
                    <div className="absolute inset-0 bg-[#064E3B]/20 flex items-end p-3">
                      <span className="bg-[#064E3B] text-white text-[9px] font-black uppercase tracking-widest px-2 py-1 rounded-full">
                        {matchCount > 0 ? `${matchCount} partidos` : 'Activo'}
                      </span>
                    </div>
                  )}
                  {!isActive && sportLoading && activeSport === sport.key && (
                    <div className="absolute inset-0 bg-white/70 flex items-center justify-center">
                      <div className="w-6 h-6 border-2 border-[#064E3B] border-t-transparent rounded-full animate-spin" />
                    </div>
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-base">{sport.flag}</span>
                    <h3 className={`font-editorial text-base font-bold transition-colors ${
                      isActive ? 'text-[#064E3B]' : 'text-[#1A1C1E] group-hover:text-[#064E3B]'
                    }`}>{sport.label}</h3>
                  </div>
                  <p className="text-[10px] font-bold text-[#64748B] uppercase tracking-widest">{sport.subtitle}</p>
                </div>
              </button>
            );
          })}
        </div>
      </section>

      {/* ── RADAR DE VALOR ───────────────────────────────────────────────── */}
      <section>
        <div className="flex flex-col md:flex-row items-center justify-between mb-12 border-b border-[#E5E7EB] pb-6">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{activeSportConfig.flag}</span>
            <h2 className="text-3xl font-editorial font-bold text-[#1A1C1E]">
              Radar de Valor — <span className="text-[#064E3B]">{activeSportConfig.label}</span>
            </h2>
          </div>
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

        {/* Loading state */}
        {sportLoading ? (
          <div className="flex flex-col items-center justify-center py-24">
            <div className="w-10 h-10 border-2 border-[#E5E7EB] border-t-[#064E3B] rounded-full animate-spin mb-4" />
            <div className="text-[10px] font-bold uppercase tracking-widest text-[#064E3B] animate-pulse">
              Cargando {activeSportConfig.label}…
            </div>
          </div>
        ) : filteredMatches.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <span className="text-5xl mb-4">{activeSportConfig.flag}</span>
            <p className="text-[#64748B] font-medium text-lg mb-2">Sin partidos disponibles</p>
            <p className="text-[10px] font-bold text-[#94A3B8] uppercase tracking-widest">
              {activeSport !== 'laliga'
                ? 'Los datos se sincronizan periódicamente con The Odds API'
                : 'El caché se actualiza cada hora'}
            </p>
          </div>
        ) : (
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
        )}
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
