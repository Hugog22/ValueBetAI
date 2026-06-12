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

interface PredictionDetail {
    bet_id: number;
    match_date: string;
    home_team: string;
    away_team: string;
    market: string;
    selection: string;
    odds_taken: number;
    stake: number;
    status: string;
    pnl: number;
    user_email: string;
}

interface PredictionsDetailData {
    period_days: number;
    total: number;
    won: number;
    lost: number;
    pending: number;
    hit_rate: number;
    total_staked: number;
    net_pnl: number;
    yield_percent: number;
    predictions: PredictionDetail[];
}

export default function BankrollPage() {
    const [stats, setStats] = useState<BankrollStats | null>(null);
    const [adminStats, setAdminStats] = useState<any>(null);
    const [predictionModal, setPredictionModal] = useState<{
        open: boolean;
        data: PredictionsDetailData | null;
        loading: boolean;
        days: number;
    }>({ open: false, data: null, loading: false, days: 7 });
    
    const [trainingModal, setTrainingModal] = useState<{
        open: boolean;
        report: string;
        loading: boolean;
    }>({ open: false, report: "", loading: false });

    const { token, user, logout } = useAuth();

    useEffect(() => {
        if (!token) return;
        fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/bankroll/stats`, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
            .then(res => res.json())
            .then(data => setStats(data))
            .catch(err => console.error("Error fetching bankroll", err));
            
        if (user?.email === 'hugodesax123@gmail.com') {
            fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/admin/system-stats`, {
                headers: { 'Authorization': `Bearer ${token}` }
            })
                .then(res => res.json())
                .then(data => setAdminStats(data))
                .catch(err => console.error("Error fetching admin stats", err));
        }
    }, [token, user]);

    const openPredictionsModal = async (days: number = 7) => {
        if (!token) return;
        setPredictionModal({ open: true, data: null, loading: true, days });
        try {
            const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
            const res = await fetch(`${API}/api/admin/predictions-detail?days=${days}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await res.json();
            setPredictionModal(prev => ({ ...prev, data, loading: false }));
        } catch (err) {
            console.error('Error fetching predictions detail', err);
            setPredictionModal(prev => ({ ...prev, loading: false }));
        }
    };

    const closePredictionsModal = () =>
        setPredictionModal({ open: false, data: null, loading: false, days: 7 });

    const openTrainingReport = async () => {
        if (!token) return;
        setTrainingModal({ open: true, report: "", loading: true });
        try {
            const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
            const res = await fetch(`${API}/api/admin/training-report`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const text = await res.text();
            setTrainingModal({ open: true, report: text, loading: false });
        } catch (err) {
            console.error('Error fetching training report', err);
            setTrainingModal({ open: true, report: "Error cargando el informe.", loading: false });
        }
    };

    const closeTrainingReport = () => setTrainingModal({ open: false, report: "", loading: false });

    const getEsName = (teamName: string): string => {
        const translations: Record<string, string> = {
            'Spain': 'España',
            'Germany': 'Alemania',
            'England': 'Inglaterra',
            'France': 'Francia',
            'Italy': 'Italia',
            'Netherlands': 'Países Bajos',
            'Belgium': 'Bélgica',
            'Switzerland': 'Suiza',
            'Poland': 'Polonia',
            'Turkey': 'Turquía',
            'Croatia': 'Croacia',
            'Denmark': 'Dinamarca',
            'Sweden': 'Suecia',
            'Norway': 'Noruega',
            'Scotland': 'Escocia',
            'Wales': 'Gales',
            'Ireland': 'Irlanda',
            'Greece': 'Grecia',
            'Czech Republic': 'República Checa',
            'Bosnia & Herzegovina': 'Bosnia y Herzegovina',
            'Bosnia-Herzegovina': 'Bosnia y Herzegovina',
            'United States': 'Estados Unidos',
            'Brazil': 'Brasil',
            'Argentina': 'Argentina',
            'South Korea': 'Corea del Sur',
            'Japan': 'Japón',
            'Morocco': 'Marruecos',
            'South Africa': 'Sudáfrica',
            'Egypt': 'Egipto',
            'Saudi Arabia': 'Arabia Saudí'
        };
        return translations[teamName] || teamName;
    };

    const getSelectionLabel = (bet: BetRecord) => {
        const sel = bet.selection.toLowerCase();
        if (sel === 'home') return getEsName(bet.home_team);
        if (sel === 'away') return getEsName(bet.away_team);
        if (sel === 'draw') return 'Empate';
        if (sel === 'over' || sel === 'over25') return 'Más de 2.5';
        if (sel === 'under' || sel === 'under25') return 'Menos de 2.5';
        return bet.selection;
    };

    return (
        <>
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

                            {/* ADMIN SYSTEM STATS */}
                            {user?.email === 'hugodesax123@gmail.com' && adminStats && (
                                <div className="mb-20">
                                    <div className="flex items-center justify-between mb-8">
                                        <div>
                                            <div className="flex items-center gap-3 mb-6">
                                                <span className="h-px w-8 bg-[#0A0F1E]"></span>
                                                <span className="text-[10px] font-bold uppercase tracking-[0.3em] text-[#0A0F1E]">Acceso Administrador</span>
                                            </div>
                                            <h2 className="text-4xl font-editorial font-bold text-[#1A1C1E]">
                                                Rendimiento <span className="italic font-light">Global del Sistema</span>
                                            </h2>
                                        </div>
                                        <button
                                            onClick={openTrainingReport}
                                            className="px-6 py-3 bg-[#0A0F1E] text-white text-xs font-bold uppercase tracking-widest rounded-xl hover:bg-[#1A2240] transition-colors flex items-center gap-2"
                                        >
                                            <span className="text-lg">⚙️</span>
                                            Informe de Entrenamiento
                                        </button>
                                    </div>
                                    
                                    {adminStats.detail || adminStats.total_predictions === undefined ? (
                                        <div className="bg-red-50 p-6 rounded-[2rem] border border-red-100 text-red-600 text-sm font-bold">
                                            Aviso: El backend aún se está actualizando o requiere reiniciarse (Respuesta: {adminStats.detail || "Datos no disponibles"}).
                                        </div>
                                    ) : (
                                        <div className="grid grid-cols-2 md:grid-cols-5 gap-6">
                                                <div
                                                    className="bg-[#0A0F1E] p-6 rounded-[2rem] shadow-xl cursor-pointer hover:bg-[#1A2240] active:scale-95 transition-all group"
                                                    onClick={() => openPredictionsModal(7)}
                                                    title="Ver detalle de predicciones"
                                                >
                                                    <div className="text-[10px] font-bold text-white/50 uppercase tracking-widest mb-2 flex items-center gap-2">
                                                        Total Predicciones
                                                        <span className="text-white/30 group-hover:text-white/60 transition-colors">↗</span>
                                                    </div>
                                                    <div className="text-3xl font-editorial font-bold text-white">{adminStats.total_predictions}</div>
                                                    <div className="text-[9px] text-white/30 mt-2 group-hover:text-white/50 transition-colors">Ver desglose semanal</div>
                                                </div>
                                            <div className="bg-emerald-50/50 p-6 rounded-[2rem] border border-emerald-100">
                                                <div className="text-[10px] font-bold text-emerald-800 uppercase tracking-widest mb-2">Acertadas</div>
                                                <div className="text-3xl font-editorial font-bold text-emerald-900">{adminStats.won_predictions}</div>
                                            </div>
                                            <div className="bg-rose-50/50 p-6 rounded-[2rem] border border-rose-100">
                                                <div className="text-[10px] font-bold text-rose-800 uppercase tracking-widest mb-2">Falladas</div>
                                                <div className="text-3xl font-editorial font-bold text-rose-900">{adminStats.lost_predictions}</div>
                                            </div>
                                            <div className="bg-[#FCF9F1] p-6 rounded-[2rem] border border-[#FFD700]/30 shadow-[0_10px_30px_rgba(255,215,0,0.05)]">
                                                <div className="text-[10px] font-bold text-[#B8860B] uppercase tracking-widest mb-2">Efectividad Global</div>
                                                <div className="text-3xl font-editorial font-bold text-[#1A1C1E]">{adminStats.hit_rate}%</div>
                                            </div>
                                            <div className="bg-white p-6 rounded-[2rem] border border-[#E5E7EB]">
                                                <div className="text-[10px] font-bold text-[#64748B] uppercase tracking-widest mb-2">Yield Hipotético</div>
                                                <div className={`text-3xl font-editorial font-bold ${adminStats.hypothetical_yield >= 0 ? 'text-[#064E3B]' : 'text-red-600'}`}>
                                                    {adminStats.hypothetical_yield >= 0 ? '+' : ''}{adminStats.hypothetical_yield}%
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}

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
                                                            {getEsName(bet.home_team)} <span className="text-[#64748B] font-sans font-medium text-sm">vs</span> {getEsName(bet.away_team)}
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
                                                            bet.status === 'Pending' ? 'bg-amber-100 text-amber-700' :
                                                            bet.status === 'Won' ? 'bg-[#064E3B]/10 text-[#064E3B]' :
                                                            bet.status === 'Lost' ? 'bg-red-50 text-red-600' :
                                                            bet.status === 'Void' ? 'bg-gray-100 text-gray-500' :
                                                            'bg-amber-100 text-amber-700'
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

        {/* PREDICTIONS DETAIL MODAL */}
        {predictionModal.open && (
            <div
                className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
                onClick={(e) => { if (e.target === e.currentTarget) closePredictionsModal(); }}
            >
                <div className="bg-[#FCF9F1] rounded-[2.5rem] shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden">

                    {/* Modal Header */}
                    <div className="flex items-center justify-between px-10 py-8 border-b border-[#E5E7EB] flex-shrink-0">
                        <div>
                            <div className="text-[10px] font-bold uppercase tracking-[0.3em] text-[#64748B] mb-1">Acceso Administrador</div>
                            <h2 className="text-3xl font-editorial font-bold text-[#1A1C1E]">
                                Detalle de <span className="italic font-light">Predicciones</span>
                            </h2>
                        </div>
                        <div className="flex items-center gap-3">
                            {/* Period selector */}
                            {[7, 14, 30].map(d => (
                                <button
                                    key={d}
                                    onClick={() => openPredictionsModal(d)}
                                    className={`px-4 py-2 rounded-xl text-[11px] font-bold uppercase tracking-wider transition-all ${
                                        predictionModal.days === d
                                            ? 'bg-[#0A0F1E] text-white'
                                            : 'bg-white border border-[#E5E7EB] text-[#64748B] hover:border-[#0A0F1E]'
                                    }`}
                                >
                                    {d}d
                                </button>
                            ))}
                            <button
                                onClick={closePredictionsModal}
                                className="ml-4 w-10 h-10 rounded-full bg-[#F1F5F9] flex items-center justify-center text-[#64748B] hover:bg-red-50 hover:text-red-600 transition-all text-xl font-bold"
                            >
                                ×
                            </button>
                        </div>
                    </div>

                    {/* Modal Body */}
                    <div className="overflow-y-auto flex-1 px-10 py-8">
                        {predictionModal.loading ? (
                            <div className="flex flex-col items-center justify-center py-24 gap-4">
                                <div className="w-10 h-10 border-4 border-[#0A0F1E]/20 border-t-[#0A0F1E] rounded-full animate-spin" />
                                <p className="text-[#64748B] font-bold text-sm">Cargando predicciones…</p>
                            </div>
                        ) : predictionModal.data ? (
                            <>
                                {/* Summary strip */}
                                <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 mb-10">
                                    <div className="bg-[#0A0F1E] p-5 rounded-2xl">
                                        <div className="text-[9px] font-bold text-white/50 uppercase tracking-widest mb-1">Total</div>
                                        <div className="text-2xl font-editorial font-bold text-white">{predictionModal.data.total}</div>
                                    </div>
                                    <div className="bg-emerald-50 border border-emerald-100 p-5 rounded-2xl">
                                        <div className="text-[9px] font-bold text-emerald-800 uppercase tracking-widest mb-1">Acertadas</div>
                                        <div className="text-2xl font-editorial font-bold text-emerald-900">{predictionModal.data.won}</div>
                                    </div>
                                    <div className="bg-rose-50 border border-rose-100 p-5 rounded-2xl">
                                        <div className="text-[9px] font-bold text-rose-800 uppercase tracking-widest mb-1">Falladas</div>
                                        <div className="text-2xl font-editorial font-bold text-rose-900">{predictionModal.data.lost}</div>
                                    </div>
                                    <div className="bg-amber-50 border border-amber-100 p-5 rounded-2xl">
                                        <div className="text-[9px] font-bold text-amber-700 uppercase tracking-widest mb-1">Efectividad</div>
                                        <div className="text-2xl font-editorial font-bold text-amber-900">{predictionModal.data.hit_rate}%</div>
                                    </div>
                                    <div className={`p-5 rounded-2xl border ${
                                        predictionModal.data.net_pnl >= 0
                                            ? 'bg-emerald-50 border-emerald-100'
                                            : 'bg-rose-50 border-rose-100'
                                    }`}>
                                        <div className={`text-[9px] font-bold uppercase tracking-widest mb-1 ${
                                            predictionModal.data.net_pnl >= 0 ? 'text-emerald-700' : 'text-rose-700'
                                        }`}>PnL Neto</div>
                                        <div className={`text-2xl font-editorial font-bold ${
                                            predictionModal.data.net_pnl >= 0 ? 'text-emerald-900' : 'text-rose-900'
                                        }`}>
                                            {predictionModal.data.net_pnl >= 0 ? '+' : ''}{predictionModal.data.net_pnl.toFixed(2)}€
                                        </div>
                                    </div>
                                </div>

                                {/* Predictions table */}
                                {predictionModal.data.predictions.length === 0 ? (
                                    <div className="text-center py-16 text-[#64748B]">
                                        <div className="text-5xl mb-4">📭</div>
                                        <p className="font-bold">No hay predicciones en los últimos {predictionModal.data.period_days} días</p>
                                    </div>
                                ) : (
                                    <div className="overflow-x-auto rounded-2xl border border-[#E5E7EB]">
                                        <table className="w-full text-sm">
                                            <thead>
                                                <tr className="bg-[#F8F9FB] border-b border-[#E5E7EB]">
                                                    <th className="px-6 py-4 text-left text-[10px] font-bold uppercase tracking-widest text-[#64748B]">Fecha</th>
                                                    <th className="px-6 py-4 text-left text-[10px] font-bold uppercase tracking-widest text-[#64748B]">Partido</th>
                                                    <th className="px-6 py-4 text-left text-[10px] font-bold uppercase tracking-widest text-[#64748B]">Selección</th>
                                                    <th className="px-6 py-4 text-right text-[10px] font-bold uppercase tracking-widest text-[#64748B]">Cuota</th>
                                                    <th className="px-6 py-4 text-center text-[10px] font-bold uppercase tracking-widest text-[#64748B]">Estado</th>
                                                    <th className="px-6 py-4 text-right text-[10px] font-bold uppercase tracking-widest text-[#64748B]">PnL</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-[#F1F5F9]">
                                                {predictionModal.data.predictions.map(pred => (
                                                    <tr key={pred.bet_id} className="bg-white hover:bg-[#F8F9FB] transition-colors">
                                                        <td className="px-6 py-4 text-[#64748B] text-xs whitespace-nowrap">
                                                            {new Date(pred.match_date).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                                                        </td>
                                                        <td className="px-6 py-4">
                                                            <div className="font-bold text-[#1A1C1E] text-xs">{getEsName(pred.home_team)}</div>
                                                            <div className="text-[#64748B] text-[10px]">vs {getEsName(pred.away_team)}</div>
                                                        </td>
                                                        <td className="px-6 py-4">
                                                            <div className="text-xs font-bold text-[#1A1C1E] capitalize">{pred.selection}</div>
                                                            <div className="text-[10px] text-[#64748B]">{pred.market}</div>
                                                        </td>
                                                        <td className="px-6 py-4 text-right">
                                                            <span className="font-bold text-sm text-[#1A1C1E]">{pred.odds_taken.toFixed(2)}</span>
                                                        </td>
                                                        <td className="px-6 py-4 text-center">
                                                            <span className={`inline-flex px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-widest ${
                                                                pred.status === 'Won' ? 'bg-emerald-100 text-emerald-700' :
                                                                pred.status === 'Lost' ? 'bg-rose-100 text-rose-700' :
                                                                pred.status === 'Void' ? 'bg-gray-100 text-gray-500' :
                                                                'bg-amber-100 text-amber-700'
                                                            }`}>
                                                                {pred.status}
                                                            </span>
                                                        </td>
                                                        <td className="px-6 py-4 text-right">
                                                            {pred.status === 'Pending' || pred.status === 'Void' ? (
                                                                <span className="text-[#64748B] text-xs">—</span>
                                                            ) : (
                                                                <span className={`font-bold text-sm ${
                                                                    pred.pnl >= 0 ? 'text-emerald-700' : 'text-rose-700'
                                                                }`}>
                                                                    {pred.pnl >= 0 ? '+' : ''}{pred.pnl.toFixed(2)}€
                                                                </span>
                                                            )}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </>
                        ) : (
                            <div className="text-center py-16 text-[#64748B]">
                                <p className="font-bold">Error cargando datos. Inténtalo de nuevo.</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        )}

        {/* TRAINING REPORT MODAL */}
        {trainingModal.open && (
            <div
                className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
                onClick={(e) => { if (e.target === e.currentTarget) closeTrainingReport(); }}
            >
                <div className="bg-[#1A1C1E] rounded-[2.5rem] shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col overflow-hidden border border-white/10">

                    {/* Modal Header */}
                    <div className="flex items-center justify-between px-10 py-6 border-b border-white/10 flex-shrink-0 bg-[#0A0F1E]">
                        <div className="flex items-center gap-4">
                            <span className="text-3xl">🤖</span>
                            <div>
                                <h2 className="text-xl font-editorial font-bold text-white">
                                    Registro de <span className="italic font-light">Autoentrenamiento IA</span>
                                </h2>
                                <div className="text-[10px] text-white/50 uppercase tracking-[0.2em] mt-1">Terminal de logs de Optuna & XGBoost</div>
                            </div>
                        </div>
                        <button
                            onClick={closeTrainingReport}
                            className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-white/50 hover:bg-white/10 hover:text-white transition-all text-xl"
                        >
                            ×
                        </button>
                    </div>

                    {/* Modal Body */}
                    <div className="flex-1 overflow-hidden p-6 bg-[#05080F]">
                        {trainingModal.loading ? (
                            <div className="flex flex-col items-center justify-center h-full gap-4">
                                <div className="w-8 h-8 border-2 border-white/20 border-t-[#00FF00] rounded-full animate-spin" />
                                <p className="text-[#00FF00] font-mono text-xs">Descargando informe del servidor...</p>
                            </div>
                        ) : (
                            <div className="h-full w-full bg-black/50 rounded-xl border border-white/5 p-6 overflow-y-auto">
                                <pre className="text-[#00FF00] font-mono text-[11px] leading-relaxed whitespace-pre-wrap">
                                    {trainingModal.report}
                                </pre>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        )}
        </>
    );
}
