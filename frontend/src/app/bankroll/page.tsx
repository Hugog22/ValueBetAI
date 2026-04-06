'use client';

import { useEffect, useState } from 'react';
import ProtectedRoute from '@/components/ProtectedRoute';
import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';

interface BankrollStats {
    total_bets: number;
    total_staked: number;
    total_pnl: number;
    roi: number;
    win_rate: number;
    current_bankroll: number;
    recent_bets: BetRecord[];
}

interface BetRecord {
    id: number;
    match_id: number;
    home_team: string;
    away_team: string;
    market: string;
    selection: string;
    odds_taken: number;
    stake: number;
    status: string;
    pnl: number;
    created_at: string;
    match_date: string;
    risk_level: string;
    risk_badge: string;
    risk_bg_class: string;
}

export default function BankrollPage() {
    const [stats, setStats] = useState<BankrollStats | null>(null);
    const { token, user, logout } = useAuth();

    useEffect(() => {
        if (!token) return;
        fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/bankroll/stats`, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
            .then(res => res.json())
            .then(data => setStats(data))
            .catch(err => console.error("Error fetching bankroll", err));
    }, [token]);

    const getSelectionLabel = (bet: BetRecord) => {
        const sel = bet.selection.toLowerCase();
        if (sel === 'home') return bet.home_team;
        if (sel === 'away') return bet.away_team;
        if (sel === 'draw') return 'Empate';
        if (sel === 'over' || sel === 'over25') return 'Más de 2.5';
        if (sel === 'under' || sel === 'under25') return 'Menos de 2.5';
        return bet.selection;
    };

    return (
        <ProtectedRoute>
            <div className="min-h-screen bg-[#FCF9F1] text-[#1A1C1E] font-sans selection:bg-[#064E3B]/10 overflow-x-hidden">

                <header className="fixed top-0 w-full z-50 glass-light border-b border-black/5">
                    <div className="max-w-7xl mx-auto px-8 h-20 flex justify-between items-center">
                        <div className="flex items-center gap-10">
                            <Link href="/" className="flex items-center gap-2">
                                <div className="h-10 w-10 bg-[#FFD700] flex items-center justify-center rounded-lg shadow-sm">
                                    <span className="text-[#1A1C1E] font-black text-xs leading-none">BET<br />AI</span>
                                </div>
                                <span className="text-xl font-editorial font-bold tracking-tight text-[#1A1C1E]">
                                    ValueBet <span className="opacity-50">AI</span>
                                </span>
                            </Link>
                        </div>
                        <nav className="flex items-center gap-8">
                            <Link href="/" className="text-sm font-bold text-[#1A1C1E] hover:text-[#064E3B] transition-colors flex items-center gap-2">
                                <span className="text-lg">←</span>
                                <span>Regresar al Radar</span>
                            </Link>
                            {user && (
                                <div className="flex items-center gap-4 border-l border-black/10 pl-8">
                                    <span className="text-[10px] uppercase tracking-widest font-bold text-[#64748B]">{user.email}</span>
                                    <button onClick={logout} className="text-[10px] uppercase tracking-widest font-bold text-red-600 hover:opacity-70 transition-colors">Salir</button>
                                </div>
                            )}
                        </nav>
                    </div>
                </header>

                <main className="pt-32 pb-24 max-w-7xl mx-auto px-8">
                    <div className="mb-16">
                        <div className="flex items-center gap-3 mb-6">
                            <span className="h-px w-8 bg-[#FFD700]"></span>
                            <span className="text-[10px] font-bold uppercase tracking-[0.3em] text-[#64748B]">Auditoría de Inversión</span>
                        </div>
                        <h1 className="text-6xl font-editorial text-[#1A1C1E] leading-tight font-bold mb-6">
                            Mi Portafolio <span className="italic font-light">Digital</span>
                        </h1>
                        <p className="text-[#64748B] text-lg font-medium max-w-2xl leading-relaxed">
                            Seguimiento avanzado de posiciones algorítmicas y análisis de rendimiento para decisiones de inversión inteligente.
                        </p>
                    </div>

                    {!stats ? (
                        <div className="flex flex-col items-center justify-center py-32">
                            <div className="w-12 h-12 border-2 border-[#E5E7EB] border-t-[#064E3B] rounded-full animate-spin mb-6"></div>
                            <div className="text-[#064E3B] text-[10px] font-bold uppercase tracking-[0.3em] animate-pulse">Sincronizando Ledger...</div>
                        </div>
                    ) : (
                        <>
                            {/* KPI GRID */}
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-20">
                                <div className="bg-[#064E3B] p-8 rounded-[2rem] shadow-[0_10px_30px_rgba(0,0,0,0.02)]">
                                    <div className="text-[10px] font-bold text-white/70 uppercase tracking-[0.2em] mb-4">Capital (Bankroll)</div>
                                    <div className="text-4xl font-editorial font-bold text-white">
                                        {(stats.current_bankroll ?? 1000).toFixed(2)} <span className="text-sm font-sans font-medium opacity-60">€</span>
                                    </div>
                                </div>
                                <div className="bg-white p-8 rounded-[2rem] border border-[#E5E7EB] shadow-[0_10px_30px_rgba(0,0,0,0.02)]">
                                    <div className="text-[10px] font-bold text-[#64748B] uppercase tracking-[0.2em] mb-4">Volumen Total</div>
                                    <div className="text-4xl font-editorial font-bold text-[#1A1C1E]">
                                        {(stats.total_staked || 0).toFixed(2)} <span className="text-sm font-sans font-medium text-[#64748B]">u.</span>
                                    </div>
                                </div>
                                <div className="bg-white p-8 rounded-[2rem] border border-[#E5E7EB] shadow-[0_10px_30px_rgba(0,0,0,0.02)]">
                                    <div className="text-[10px] font-bold text-[#64748B] uppercase tracking-[0.2em] mb-4">PnL Neto</div>
                                    <div className={`text-4xl font-editorial font-bold ${(stats.total_pnl ?? 0) >= 0 ? 'text-[#064E3B]' : 'text-red-600'}`}>
                                        {(stats.total_pnl ?? 0) >= 0 ? '+' : ''}{(stats.total_pnl ?? 0).toFixed(2)} <span className="text-sm font-sans font-medium opacity-60">u.</span>
                                    </div>
                                </div>
                                <div className="bg-white p-8 rounded-[2rem] border border-[#E5E7EB] shadow-[0_10px_30px_rgba(0,0,0,0.02)]">
                                    <div className="text-[10px] font-bold text-[#64748B] uppercase tracking-[0.2em] mb-4">ROI Histórico</div>
                                    <div className={`text-4xl font-editorial font-bold ${(stats.roi || 0) >= 0 ? 'text-[#064E3B]' : 'text-red-600'}`}>
                                        {(stats.roi || 0) >= 0 ? '+' : ''}{(stats.roi || 0).toFixed(2)}%
                                    </div>
                                </div>
                                <div className="bg-white p-8 rounded-[2rem] border border-[#E5E7EB] shadow-[0_10px_30px_rgba(0,0,0,0.02)] bg-gradient-to-br from-[#064E3B]/5 to-transparent">
                                    <div className="text-[10px] font-bold text-[#064E3B] uppercase tracking-[0.2em] mb-4">Efectividad</div>
                                    <div className="text-4xl font-editorial font-bold text-[#1A1C1E]">{(stats.win_rate || 0).toFixed(1)}%</div>
                                </div>
                            </div>

                            <div className="flex items-center justify-between mb-10 border-b border-[#E5E7EB] pb-6">
                                <h2 className="text-3xl font-editorial font-bold text-[#1A1C1E]">Libro de Órdenes</h2>
                                <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-[0.2em]">{(stats.recent_bets || []).length} Operaciones</span>
                            </div>

                            <div className="bg-white rounded-[2rem] border border-[#E5E7EB] overflow-hidden shadow-[0_10px_30px_rgba(0,0,0,0.02)]">
                                <div className="overflow-x-auto">
                                    <table className="min-w-full">
                                        <thead>
                                            <tr className="bg-[#F8F9FA] border-b border-[#E5E7EB]">
                                                <th className="px-8 py-5 text-left text-[10px] font-bold text-[#64748B] uppercase tracking-[0.2em]">Fecha</th>
                                                <th className="px-8 py-5 text-left text-[10px] font-bold text-[#64748B] uppercase tracking-[0.2em]">Mercado / Selección</th>
                                                <th className="px-8 py-5 text-left text-[10px] font-bold text-[#64748B] uppercase tracking-[0.2em]">Nivel de Riesgo</th>
                                                <th className="px-8 py-5 text-left text-[10px] font-bold text-[#64748B] uppercase tracking-[0.2em]">Stake / Cuota</th>
                                                <th className="px-8 py-5 text-left text-[10px] font-bold text-[#64748B] uppercase tracking-[0.2em]">Estado</th>
                                                <th className="px-8 py-5 text-right text-[10px] font-bold text-[#64748B] uppercase tracking-[0.2em]">Resultado</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-[#E5E7EB]">
                                            {(stats.recent_bets || []).length === 0 ? (
                                                <tr>
                                                    <td colSpan={5} className="px-8 py-20 text-center text-[#64748B] font-medium italic">No se han registrado operaciones en el Ledger.</td>
                                                </tr>
                                            ) : stats.recent_bets.map((bet) => (
                                                <tr key={bet.id} className="hover:bg-[#F8F9FA] transition-colors group">
                                                    <td className="px-8 py-6">
                                                        <div className="text-sm font-bold text-[#1A1C1E] capitalize">
                                                            {new Intl.DateTimeFormat('es-ES', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(bet.match_date || bet.created_at))}
                                                        </div>
                                                    </td>
                                                    <td className="px-8 py-6">
                                                        <div className="font-editorial text-lg font-bold text-[#1A1C1E] group-hover:text-[#064E3B] transition-colors line-clamp-1 mb-1">
                                                            {bet.home_team} <span className="text-[#64748B] font-sans font-medium text-sm">v</span> {bet.away_team}
                                                        </div>
                                                        <div className="text-[10px] text-[#64748B] font-bold uppercase tracking-widest">
                                                            <span className="opacity-60">{bet.market}: </span> 
                                                            <span className="text-[#1A1C1E]">{getSelectionLabel(bet)}</span>
                                                        </div>
                                                    </td>
                                                    <td className="px-8 py-6">
                                                        <span className={`${bet.risk_bg_class || 'bg-gray-100 text-gray-600'} px-3 py-1 rounded-lg text-[9px] font-black tracking-widest uppercase`}>
                                                            {bet.risk_level || 'N/D'}
                                                        </span>
                                                    </td>
                                                    <td className="px-8 py-6">
                                                        <div className="text-sm font-bold text-[#1A1C1E] mb-1">{bet.stake} <span className="text-[10px] font-medium opacity-50">u.</span></div>
                                                        <div className="inline-block px-2 py-0.5 bg-[#F1F3F5] text-[#1A1C1E] text-[10px] font-black rounded-lg">{bet.odds_taken.toFixed(2)}</div>
                                                    </td>
                                                    <td className="px-8 py-6">
                                                        <span className={`px-4 py-1.5 text-[10px] font-black tracking-widest rounded-full uppercase ${
                                                            bet.status === 'PENDING' ? 'bg-amber-100 text-amber-700' :
                                                            bet.status === 'WON' ? 'bg-[#064E3B]/10 text-[#064E3B]' :
                                                            'bg-red-50 text-red-600'
                                                        }`}>
                                                            {bet.status}
                                                        </span>
                                                    </td>
                                                    <td className="px-8 py-6 text-right">
                                                        <div className={`text-xl font-editorial font-bold ${(bet.pnl ?? 0) > 0 ? 'text-[#064E3B]' : (bet.pnl ?? 0) < 0 ? 'text-red-600' : 'text-[#64748B]'}`}>
                                                            {(bet.pnl ?? 0) > 0 ? '+' : ''}{(bet.pnl ?? 0).toFixed(2)}
                                                        </div>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </>
                    )}
                </main>
            </div>
        </ProtectedRoute>
    );
}
