import Link from 'next/link';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#051209] text-white font-sans selection:bg-[#C0FF00]/30 selection:text-[#C0FF00] overflow-hidden relative">
      
      {/* Background Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-[#C0FF00]/[0.03] blur-[120px] rounded-full pointer-events-none"></div>

      {/* Navigation */}
      <nav className="absolute top-0 w-full flex items-center justify-between px-8 py-6 z-50 max-w-7xl mx-auto left-0 right-0">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 bg-[#FFD700] flex items-center justify-center rounded-xl shadow-lg shadow-[#FFD700]/20">
            <span className="text-[#1A1C1E] font-black text-[10px] leading-none">BET<br />AI</span>
          </div>
          <span className="font-editorial font-bold text-xl tracking-tight">
            ValueBet <span className="opacity-50">AI</span>
          </span>
        </div>
        <div className="flex items-center gap-6">
          <Link href="/login" className="text-sm font-medium text-white/70 hover:text-white transition-colors">
            Iniciar sesión
          </Link>
          <Link href="/register" className="text-sm font-bold bg-white text-[#051209] px-5 py-2.5 rounded-full hover:bg-white/90 transition-transform hover:scale-105 active:scale-95">
            Crear cuenta
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4 pt-20 pb-12 text-center max-w-5xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 mb-8 backdrop-blur-sm">
          <span className="w-2 h-2 rounded-full bg-[#C0FF00] animate-pulse"></span>
          <span className="text-xs font-semibold tracking-widest uppercase text-[#C0FF00]">Modelo v2.0 Activo</span>
        </div>
        
        <h1 className="text-6xl md:text-8xl font-editorial font-bold tracking-tight leading-[1.1] mb-8">
          La ventaja <span className="italic font-light text-white/70">injusta</span><br />
          en apuestas deportivas
        </h1>
        
        <p className="text-lg md:text-xl text-white/60 max-w-2xl mx-auto font-light leading-relaxed mb-12">
          Nuestra inteligencia artificial analiza miles de puntos de datos para identificar oportunidades de valor que el mercado pasa por alto.
        </p>

        <div className="flex items-center justify-center gap-4 mb-24">
          <Link href="/register" className="flex items-center justify-center gap-2 bg-[#C0FF00] text-[#051209] font-black text-sm uppercase tracking-widest px-8 py-4 rounded-full hover:bg-[#a8e000] shadow-[0_0_40px_rgba(192,255,0,0.3)] transition-all hover:scale-105 active:scale-95">
            Comenzar ahora
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </Link>
        </div>

        {/* Stats Chart Section */}
        <div className="w-full max-w-4xl mx-auto bg-white/[0.02] border border-white/5 rounded-3xl p-8 md:p-12 backdrop-blur-xl shadow-2xl relative overflow-hidden text-left">
          <div className="absolute top-0 right-0 w-64 h-64 bg-[#C0FF00]/10 blur-[80px] rounded-full pointer-events-none -translate-y-1/2 translate-x-1/3"></div>
          
          <div className="mb-10">
            <h2 className="text-2xl font-editorial font-bold mb-2">Precisión del Modelo Predictivo</h2>
            <p className="text-white/50 text-sm">Basado en el historial de apuestas calificadas en el último trimestre.</p>
          </div>

          <div className="space-y-8">
            {/* Low Risk */}
            <div>
              <div className="flex justify-between items-end mb-3">
                <div>
                  <h3 className="text-sm font-bold uppercase tracking-wider text-white/90">Riesgo Bajo</h3>
                  <p className="text-xs text-white/40 mt-1">Alta probabilidad de éxito, cuotas conservadoras</p>
                </div>
                <div className="text-3xl font-editorial font-bold text-[#C0FF00]">85%</div>
              </div>
              <div className="w-full h-3 bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-[#064E3B] to-[#C0FF00] rounded-full relative" style={{ width: '85%' }}>
                  <div className="absolute inset-0 bg-[linear-gradient(45deg,rgba(255,255,255,0.15)_25%,transparent_25%,transparent_50%,rgba(255,255,255,0.15)_50%,rgba(255,255,255,0.15)_75%,transparent_75%,transparent)] bg-[length:1rem_1rem] animate-[stripes_1s_linear_infinite]"></div>
                </div>
              </div>
            </div>

            {/* Medium Risk */}
            <div>
              <div className="flex justify-between items-end mb-3">
                <div>
                  <h3 className="text-sm font-bold uppercase tracking-wider text-white/90">Riesgo Medio</h3>
                  <p className="text-xs text-white/40 mt-1">Balance óptimo entre probabilidad y cuota</p>
                </div>
                <div className="text-3xl font-editorial font-bold text-[#FFD700]">70%</div>
              </div>
              <div className="w-full h-3 bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-[#B45309] to-[#FFD700] rounded-full relative" style={{ width: '70%' }}>
                  <div className="absolute inset-0 bg-[linear-gradient(45deg,rgba(255,255,255,0.15)_25%,transparent_25%,transparent_50%,rgba(255,255,255,0.15)_50%,rgba(255,255,255,0.15)_75%,transparent_75%,transparent)] bg-[length:1rem_1rem] animate-[stripes_1s_linear_infinite]"></div>
                </div>
              </div>
            </div>
          </div>
        </div>

      </main>
      
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes stripes {
          0% { background-position: 1rem 0; }
          100% { background-position: 0 0; }
        }
      `}} />
    </div>
  );
}
