'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';
import FeaturedBet from '@/components/FeaturedBet';
import BentoCard from '@/components/BentoCard';
import BetModal from '@/components/BetModal';
import AllOptionsModal from '@/components/AllOptionsModal';
import AnalysisModal from '@/components/AnalysisModal';
import WorldCupBanner from '@/components/WorldCupBanner';
import { getFlag, getEsName } from '@/utils/translations';

// Safelist for Tailwind JIT (backend-generated classes)
const _tailwindSafelist = 'bg-green-600 bg-yellow-400 bg-yellow-600 bg-orange-500 bg-red-600 bg-red-900 text-white text-black font-bold font-black';

const API = '/api/proxy';

// ── Sport Config ─────────────────────────────────────────────────────────────

const SPORTS = [
  {
    key:      'worldcup',
    label:    'Mundial 2026',
    subtitle: 'FIFA World Cup',
    flag:     '⚽',
    image:    '/maradona.jpg',
    isWorldCup: true,
    isOffSeason: false, // World Cup is never off-season
  },
  {
    key:      'laliga',
    label:    'La Liga',
    subtitle: 'España',
    flag:     '🇪🇸',
    image:    'https://images.unsplash.com/photo-1574629810360-7efbbe195018?q=80&w=400&h=400&auto=format&fit=crop',
    isWorldCup: false,
    isOffSeason: true, // Off until September 2026
  },
  {
    key:      'premier',
    label:    'Premier League',
    subtitle: 'Inglaterra',
    flag:     '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
    image:    'https://images.unsplash.com/photo-1522778119026-d647f0596c20?q=80&w=400&h=400&auto=format&fit=crop',
    isWorldCup: false,
    isOffSeason: true, // Off until August 2026
  },
  {
    key:      'champions',
    label:    'Champions',
    subtitle: 'Europa',
    flag:     '🏆',
    image:    'https://images.unsplash.com/photo-1614632537190-23e4146777db?q=80&w=400&h=400&auto=format&fit=crop',
    isWorldCup: false,
    isOffSeason: true, // Off until September 2026
  },
] as const;

type SportKey = typeof SPORTS[number]['key'];
type SportConfig = typeof SPORTS[number];

// ── Types ─────────────────────────────────────────────────────────────────────

interface Risk { level: string; badge: string; bgClass: string; }

interface PickData {
  market: string; outcome: string;
  bookmaker_odds?: number; bookmakerOdds?: number;
  stake?: number; label: string;
  isValueBet?: boolean; ev?: number; probability?: number;
  risk?: Risk; bookmaker_implied_prob?: number;
}

interface BookmakerOdds {
  title: string;
  home_odds: number;
  draw_odds: number;
  away_odds: number;
}

interface Match {
  id: number; date: string;
  homeTeam: string; awayTeam: string;
  sport?: string;
  bestPick?: PickData; topPicks?: PickData[];
  isSteam?: boolean; justification?: string;
  all_bookmakers?: BookmakerOdds[];
  allCandidates?: PickData[];
  // World Cup specific
  homeFifaPts?: number; awayFifaPts?: number;
  homeSquadQuality?: number; awaySquadQuality?: number;
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
  initialWorldCupMatches?: Match[];
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function MatchesDashboard({ initialMatches, initialParlay, initialWorldCupMatches }: Props) {
  const { token } = useAuth();

  // Sport selector — default to worldcup (MODO MUNDIAL)
  const [activeSport, setActiveSport] = useState<SportKey>('worldcup');
  const [sportLoading, setSportLoading] = useState(false);

  // Match data — World Cup seeded from ISR, others lazy-loaded
  const [matchesBySport, setMatchesBySport] = useState<Record<SportKey, Match[]>>({
    worldcup:  initialWorldCupMatches ?? [],
    laliga:    initialMatches,
    premier:   [],
    champions: [],
  });

  // Track which sports have been fetched (even if empty) to avoid repeated requests
  const fetchedSports = useRef<Set<SportKey>>(new Set<SportKey>());

  // Parlays — seeded from ISR, refreshed from API
  const [allParlays, setAllParlays] = useState<ParlayData[]>(
    initialParlay?.legs?.length
      ? [initialParlay]
      : []
  );

  // UI state
  const [filterRisk, setFilterRisk] = useState<string>('all');
  const [minEV,      setMinEV]      = useState<number>(0);
  const [bankroll,   setBankroll]   = useState<number>(0);

  // Modals state
  const [activeBet, setActiveBet] = useState<{
    matchId: number;
    homeTeam: string;
    awayTeam: string;
    market: string;
    outcome: string;
    label: string;
    odds: number;
    probability: number;
    ev: number;
    bookmaker: string;
  } | null>(null);
  const [activeOptionsMatch, setActiveOptionsMatch] = useState<Match | null>(null);
  const [activeAnalysisMatch, setActiveAnalysisMatch] = useState<Match | null>(null);

  // Fetch bankroll
  useEffect(() => {
    if (!token) return;
    fetch(`${API}/bankroll/stats`, { headers: {} })
      .then(r => {
        if (!r.ok) throw new Error("Failed to fetch bankroll");
        return r.json();
      })
      .then(d => setBankroll(d.current_bankroll ?? 0))
      .catch((e) => {
        console.error("Error fetching bankroll", e);
        setBankroll(0);
      });
  }, [token]);

  // Fetch all parlays from API
  useEffect(() => {
    fetch(`${API}/sports/all_parlays`)
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data) && data.length > 0) setAllParlays(data);
      })
      .catch(() => {});
  }, []);

  // Fetch matches for a sport on demand — respects off-season and deduplication
  const fetchSport = useCallback(async (sport: SportKey) => {
    const sportConfig = SPORTS.find(s => s.key === sport);

    // IMPORTANT: Never fetch for off-season sports
    if (sportConfig?.isOffSeason) return;

    // Already fetched this sport (even if it returned 0 results)
    if (fetchedSports.current.has(sport)) return;

    fetchedSports.current.add(sport);
    setSportLoading(true);

    try {
      const res = await fetch(`${API}/matches/${sport}/jornada`);
      if (!res.ok) return;
      const data = await res.json();
      const matches: Match[] = Array.isArray(data) ? data : (data?.data ?? []);
      setMatchesBySport(prev => ({ ...prev, [sport]: matches }));
    } catch { /* silent */ }
    finally { setSportLoading(false); }
  }, []);

  // Trigger fetch when sport changes
  useEffect(() => {
    fetchSport(activeSport);
  }, [activeSport, fetchSport]);

  const handleSimulateBet = (matchId: number, pick: PickData, homeTeam: string, awayTeam: string) => {
    if (!token) { alert('Accede a tu cuenta para registrar apuestas.'); return; }
    setActiveBet({
      matchId, homeTeam, awayTeam,
      market:      pick.market,
      bookmaker:   (pick as any).bookmaker || 'Bet365',
      outcome:     pick.outcome,
      label:       pick.label,
      odds:        pick.bookmaker_odds ?? pick.bookmakerOdds ?? 1.0,
      probability: pick.probability ?? 0,
      ev:          pick.ev ?? 0,
    });
  };

  const activeSportConfig = SPORTS.find(s => s.key === activeSport) as SportConfig;
  const activeMatches     = matchesBySport[activeSport] ?? [];
  const filteredMatches   = activeMatches.filter(m => {
    const riskLevel  = m.bestPick?.risk?.level || 'N/D';
    const matchesRisk = filterRisk === 'all' || riskLevel === filterRisk;
    const matchesEV   = (m.bestPick?.ev || 0) >= minEV;
    return matchesRisk && matchesEV;
  });

  const featuredMatch = activeMatches.find(m => m.bestPick?.isValueBet) || activeMatches[0];
  const isWorldCupActive = activeSport === 'worldcup';

  return (
    <>
      {/* ── WORLD CUP BANNER ────────────────────────────────────────────── */}
      {isWorldCupActive && (
        <section className="mb-16">
          <WorldCupBanner matchCount={activeMatches.length} />
        </section>
      )}

      {/* ── HERO / FEATURED ─────────────────────────────────────────────── */}
      {featuredMatch && !activeSportConfig.isOffSeason && (
        <section className="mb-20">
          <FeaturedBet
            homeTeam={getEsName(featuredMatch.homeTeam)}
            awayTeam={getEsName(featuredMatch.awayTeam)}
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
            hasOptions={!!(featuredMatch.allCandidates && featuredMatch.allCandidates.length > 0)}
            onViewAllOptions={() => setActiveOptionsMatch(featuredMatch)}
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
            {allParlays.filter(p => p.legs?.length > 0).map((parlay, pi) => {
              const isWcParlay = parlay.sport === 'worldcup';
              return (
                <div
                  key={pi}
                  className={`relative overflow-hidden rounded-[2rem] shadow-xl p-8 ${
                    isWcParlay
                      ? 'wc-card text-white'
                      : 'bg-gradient-to-br from-[#064E3B] to-[#043327] text-white'
                  }`}
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
                      <div className={`text-3xl font-editorial font-bold ${isWcParlay ? 'text-amber-300' : 'text-[#FFD700]'}`}>
                        {parlay.totalOdds?.toFixed(2)}
                      </div>
                    </div>
                  </div>

                  {/* Legs */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
                    {(parlay.legs || []).map((leg, li) => (
                      <div key={li} className="bg-white/10 backdrop-blur-md p-4 rounded-xl border border-white/10">
                        <div className="text-[10px] font-bold text-white/60 uppercase tracking-widest mb-1 truncate">
                          {isWcParlay
                            ? `${getFlag(leg.homeTeam)} ${getEsName(leg.homeTeam)} vs ${getEsName(leg.awayTeam)} ${getFlag(leg.awayTeam)}`
                            : `${getEsName(leg.homeTeam)} vs ${getEsName(leg.awayTeam)}`
                          }
                        </div>
                        <div className="flex justify-between items-end">
                          <div>
                            <div className={`text-[10px] font-bold mb-0.5 ${isWcParlay ? 'text-amber-300' : 'text-[#FFD700]'}`}>{leg.market}</div>
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
                      Prob. IA: <span className={isWcParlay ? 'text-amber-300' : 'text-[#FFD700]'}>{parlay.jointProbability?.toFixed(1)}%</span>
                    </div>
                    <button
                      onClick={() => setActiveSport(parlay.sport as SportKey)}
                      className={`font-black text-xs px-5 py-2 rounded-full hover:scale-105 transition-transform active:scale-95 ${
                        isWcParlay
                          ? 'bg-amber-400 text-[#0A0F1E]'
                          : 'bg-[#FFD700] text-[#1A1C1E]'
                      }`}
                    >
                      Ver partidos →
                    </button>
                  </div>

                  <div className="absolute -right-16 -bottom-16 w-64 h-64 bg-white/5 rounded-full blur-3xl pointer-events-none" />
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* ── EXPLORAR MERCADOS — Sport Selector ───────────────────────────── */}
      <section id="explorar-mercados" className="py-20 bg-[#FCF9F1]">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-3xl font-editorial font-bold text-[#1A1C1E]">Explorar Mercados</h2>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {SPORTS.map(sport => {
            const isActive    = activeSport === sport.key;
            const matchCount  = matchesBySport[sport.key].length;
            const isOffSeason = sport.isOffSeason;
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
                  isActive
                    ? sport.isWorldCup
                      ? 'border-amber-400 shadow-lg shadow-amber-400/20'
                      : 'border-[#064E3B] shadow-lg shadow-[#064E3B]/20'
                    : 'border-transparent group-hover:border-[#E5E7EB]'
                }`}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={sport.image}
                    alt={sport.label}
                    className={`w-full h-full object-cover transition-all duration-500 group-hover:scale-110 ${
                      isActive ? 'grayscale-0' : 'grayscale group-hover:grayscale-0'
                    }`}
                  />

                  {/* Active badge */}
                  {isActive && !isOffSeason && (
                    <div className={`absolute inset-0 flex items-end p-3 ${
                      sport.isWorldCup ? 'bg-amber-400/20' : 'bg-[#064E3B]/20'
                    }`}>
                      <span className={`text-white text-[9px] font-black uppercase tracking-widest px-2 py-1 rounded-full ${
                        sport.isWorldCup ? 'bg-amber-500' : 'bg-[#064E3B]'
                      }`}>
                        {matchCount > 0 ? `${matchCount} partidos` : 'Activo'}
                      </span>
                    </div>
                  )}

                  {/* Off-season overlay */}
                  {isOffSeason && (
                    <div className="absolute inset-0 bg-[#1A1C1E]/70 flex flex-col items-center justify-center gap-2 p-3">
                      <span className="text-2xl">💤</span>
                      <span className="text-white text-[9px] font-black uppercase tracking-widest text-center leading-tight px-2">
                        Off Season<br/>Sep 2026
                      </span>
                    </div>
                  )}

                  {/* Loading spinner */}
                  {!isOffSeason && sportLoading && activeSport === sport.key && (
                    <div className="absolute inset-0 bg-white/70 flex items-center justify-center">
                      <div className="w-6 h-6 border-2 border-[#064E3B] border-t-transparent rounded-full animate-spin" />
                    </div>
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-base">{sport.flag}</span>
                    <h3 className={`font-editorial text-base font-bold transition-colors ${
                      isActive
                        ? sport.isWorldCup ? 'text-amber-600' : 'text-[#064E3B]'
                        : 'text-[#1A1C1E] group-hover:text-[#064E3B]'
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
      <section id="radar-de-valor" className="py-24">
        <div className="flex flex-col md:flex-row items-center justify-between mb-12 border-b border-[#E5E7EB] pb-6">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{activeSportConfig.flag}</span>
            <h2 className="text-3xl font-editorial font-bold text-[#1A1C1E]">
              Radar de Valor —{' '}
              <span className={isWorldCupActive ? 'text-amber-600' : 'text-[#064E3B]'}>
                {activeSportConfig.label}
              </span>
            </h2>
          </div>

          {/* Filters — hidden for off-season sports */}
          {!activeSportConfig.isOffSeason && (
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
          )}
        </div>

        {/* Off-season state */}
        {activeSportConfig.isOffSeason ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="badge-off-season inline-flex items-center gap-2 px-6 py-3 rounded-full text-sm font-bold mb-6">
              <span>💤</span>
              <span>Temporada Finalizada</span>
            </div>
            <span className="text-6xl mb-6">{activeSportConfig.flag}</span>
            <h3 className="text-[#1A1C1E] font-editorial text-2xl font-bold mb-3">
              {activeSportConfig.label} en pausa
            </h3>
            <p className="text-[#64748B] font-medium text-base mb-2 max-w-sm">
              La temporada ha finalizado. La IA está recopilando datos de esta temporada
              y preparándose para la siguiente.
            </p>
            <p className="text-[10px] font-bold text-[#94A3B8] uppercase tracking-widest mb-8">
              Próxima temporada: Septiembre 2026
            </p>
            <button
              onClick={() => setActiveSport('worldcup')}
              className="inline-flex items-center gap-2 bg-gradient-to-r from-[#0A0F1E] to-[#1B2A4A] text-white font-bold px-6 py-3 rounded-full hover:scale-105 transition-transform active:scale-95"
            >
              <span>⚽</span>
              <span>Ver el Mundial 2026</span>
            </button>
          </div>
        ) : sportLoading ? (
          <div className="flex flex-col items-center justify-center py-24">
            <div className={`w-10 h-10 border-2 border-[#E5E7EB] rounded-full animate-spin mb-4 ${
              isWorldCupActive ? 'border-t-amber-400' : 'border-t-[#064E3B]'
            }`} />
            <div className={`text-[10px] font-bold uppercase tracking-widest animate-pulse ${
              isWorldCupActive ? 'text-amber-600' : 'text-[#064E3B]'
            }`}>
              Cargando {activeSportConfig.label}…
            </div>
          </div>
        ) : filteredMatches.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <span className="text-5xl mb-4">{activeSportConfig.flag}</span>
            <p className="text-[#64748B] font-medium text-lg mb-2">Sin partidos disponibles</p>
            <p className="text-[10px] font-bold text-[#94A3B8] uppercase tracking-widest">
              Los datos se sincronizan periódicamente
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {filteredMatches.map(match => (
              <div
                key={match.id}
                className={isWorldCupActive ? 'wc-card rounded-[2rem] overflow-hidden' : ''}
              >
                <BentoCard key={match.id} className={`flex flex-col h-full ${isWorldCupActive ? '!bg-transparent !border-none' : ''}`}>
                  {/* World Cup match header with flags */}
                  {isWorldCupActive ? (
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <span className="text-[10px] font-bold text-amber-400/80 uppercase tracking-widest block mb-1">
                          {new Date(match.date).toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                        </span>
                        <h3 className="text-lg font-editorial font-bold text-white">
                          {getFlag(match.homeTeam)} {getEsName(match.homeTeam)}
                        </h3>
                        <div className="text-white/40 text-xs font-bold my-0.5">vs</div>
                        <h3 className="text-lg font-editorial font-bold text-white">
                          {getFlag(match.awayTeam)} {getEsName(match.awayTeam)}
                        </h3>
                      </div>
                      {match.bestPick?.risk && (
                        <div className={`${match.bestPick.risk.bgClass} px-3 py-1 rounded-lg text-[8px] font-bold uppercase tracking-widest`}>
                          {match.bestPick.risk.level}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="flex justify-between items-start mb-6">
                      <div>
                        <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-widest block mb-1">
                          {new Date(match.date).toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                        </span>
                        <h3 className="text-xl font-editorial font-bold text-[#1A1C1E]">{getEsName(match.homeTeam)} vs {getEsName(match.awayTeam)}</h3>
                      </div>
                      {match.bestPick?.risk && (
                        <div className={`${match.bestPick.risk.bgClass} px-3 py-1 rounded-lg text-[8px] font-bold uppercase tracking-widest`}>
                          {match.bestPick.risk.level}
                        </div>
                      )}
                    </div>
                  )}

                  {/* FIFA ranking bar for World Cup matches */}
                  {isWorldCupActive && match.homeFifaPts && match.awayFifaPts && (
                    <div className="mb-4 space-y-2">
                      <div className="flex items-center justify-between text-[10px] text-white/50 font-bold uppercase tracking-widest">
                        <span>Ranking FIFA</span>
                        <span>{match.homeFifaPts.toFixed(0)} vs {match.awayFifaPts.toFixed(0)} pts</span>
                      </div>
                      <div className="relative h-1.5 bg-white/10 rounded-full overflow-hidden">
                        <div
                          className="fifa-rank-bar absolute left-0 top-0 h-full"
                          style={{ width: `${(match.homeFifaPts / (match.homeFifaPts + match.awayFifaPts)) * 100}%` }}
                        />
                      </div>
                    </div>
                  )}

                  <div className="mt-auto space-y-4">
                    {(match.bestPick ? [match.bestPick] : []).map((pick, pi) => (
                      <div key={pi} className="group">
                        <div className="flex items-center justify-between mb-3">
                          <span className={`text-[10px] font-bold uppercase tracking-widest ${
                            isWorldCupActive ? 'text-amber-400/80' : 'text-[#64748B]'
                          }`}>{pick.market}</span>
                          <span className={`text-xs font-bold ${isWorldCupActive ? 'text-amber-300' : 'text-[#064E3B]'}`}>
                            AI {((pick.probability ?? 0) * 100).toFixed(0)}% vs Media {((pick.bookmaker_implied_prob ?? 0) * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="flex flex-wrap items-center justify-between gap-3 md:gap-4">
                          <div className={`text-base md:text-lg font-editorial font-bold pr-2 ${isWorldCupActive ? 'text-white' : 'text-[#1A1C1E]'}`}>
                            {pick.label}
                          </div>
                          <div className="flex items-center gap-1.5 md:gap-2 ml-auto">
                            {match.justification && (
                              <button
                                onClick={() => setActiveAnalysisMatch(match)}
                                className={`text-[9px] md:text-[10px] font-bold uppercase tracking-widest px-2 md:px-3 py-1 md:py-1.5 rounded-lg border transition-colors whitespace-nowrap ${
                                  isWorldCupActive 
                                    ? 'border-white/20 text-white/70 hover:bg-white/10 hover:text-white' 
                                    : 'border-[#E5E7EB] text-[#64748B] hover:bg-[#F1F3F5] hover:text-[#1A1C1E]'
                                }`}
                              >
                                Análisis IA
                              </button>
                            )}
                            {match.allCandidates && match.allCandidates.length > 0 && (
                              <button
                                onClick={() => setActiveOptionsMatch(match)}
                                className={`text-[9px] md:text-[10px] font-bold uppercase tracking-widest px-2 md:px-3 py-1 md:py-1.5 rounded-lg border transition-colors whitespace-nowrap ${
                                  isWorldCupActive 
                                    ? 'border-white/20 text-white/70 hover:bg-white/10 hover:text-white' 
                                    : 'border-[#E5E7EB] text-[#64748B] hover:bg-[#F1F3F5] hover:text-[#1A1C1E]'
                                }`}
                              >
                                Ver opciones
                              </button>
                            )}
                            <button
                              onClick={() => handleSimulateBet(match.id, pick, match.homeTeam, match.awayTeam)}
                              className={`font-black px-2 md:px-4 py-1.5 md:py-2 rounded-xl transition-all active:scale-95 min-w-[50px] md:min-w-[60px] text-xs md:text-sm ${
                              isWorldCupActive
                                ? 'bg-white/10 hover:bg-amber-400 hover:text-[#0A0F1E] text-white border border-white/20'
                                : 'bg-[#F1F3F5] hover:bg-[#064E3B] hover:text-white text-[#1A1C1E]'
                            }`}
                          >
                            {(pick.bookmaker_odds || pick.bookmakerOdds || 1.0).toFixed(2)}
                          </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </BentoCard>
              </div>
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

      {/* ── ALL OPTIONS MODAL ───────────────────────────────────────────────── */}
      {activeOptionsMatch && (
        <AllOptionsModal
          homeTeam={getEsName(activeOptionsMatch.homeTeam)}
          awayTeam={getEsName(activeOptionsMatch.awayTeam)}
          allCandidates={activeOptionsMatch.allCandidates || []}
          onClose={() => setActiveOptionsMatch(null)}
          onSimulateBet={(candidate) => {
            handleSimulateBet(activeOptionsMatch.id, candidate, activeOptionsMatch.homeTeam, activeOptionsMatch.awayTeam);
            setActiveOptionsMatch(null);
          }}
        />
      )}

      {/* ── ANALYSIS MODAL ───────────────────────────────────────────────── */}
      {activeAnalysisMatch && (
        <AnalysisModal
          homeTeam={getEsName(activeAnalysisMatch.homeTeam)}
          awayTeam={getEsName(activeAnalysisMatch.awayTeam)}
          justification={activeAnalysisMatch.justification || ''}
          onClose={() => setActiveAnalysisMatch(null)}
        />
      )}
    </>
  );
}
