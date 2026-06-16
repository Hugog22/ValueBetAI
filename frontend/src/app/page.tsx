import Link from 'next/link';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#051209] text-white font-sans selection:bg-[#C0FF00]/30 selection:text-[#C0FF00] overflow-x-hidden relative">
      
      {/* Background elements */}
      <div className="fixed top-0 left-0 w-full h-[800px] bg-gradient-to-b from-[#064E3B]/20 to-transparent pointer-events-none" />
      <div className="fixed -top-[20%] -right-[10%] w-[70vw] h-[70vw] rounded-full bg-[#C0FF00]/[0.03] blur-[120px] pointer-events-none" />
      
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 px-8 py-6 flex justify-between items-center backdrop-blur-md bg-[#051209]/80 border-b border-white/5">
        <div className="text-xl font-editorial font-bold text-white tracking-wide">
          ValueBet AI<span className="text-[#C0FF00]">.</span>
        </div>
        <div className="flex gap-4">
          <Link href="/login" className="px-5 py-2.5 rounded-full text-sm font-bold text-[#94a3b8] hover:text-white transition-colors">
            Iniciar sesión
          </Link>
          <Link href="/register" className="px-5 py-2.5 rounded-full text-sm font-bold bg-[#C0FF00] text-[#051209] hover:bg-[#a3d900] transition-colors shadow-[0_0_20px_rgba(192,255,0,0.2)]">
            Comenzar
          </Link>
        </div>
      </nav>

      <main className="relative z-10 pt-32 lg:pt-40 pb-24 max-w-5xl mx-auto px-8">
        
        {/* HERO SECTION */}
        <div className="mb-32">
          <div className="inline-flex items-center gap-2 bg-[#064E3B]/30 border border-[#064E3B] text-[#C0FF00] px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest mb-6">
            <div className="w-1.5 h-1.5 rounded-full bg-[#C0FF00] animate-pulse"></div>
            Modo Mundial 2026 · En vivo
          </div>
          
          <h1 className="text-4xl lg:text-6xl font-editorial font-bold leading-[1.1] mb-8 text-balance">
            Sistema de <i className="text-[#94a3b8] font-normal">Inteligencia Artificial</i> para detectar cuotas rentables en tiempo real.
          </h1>
          
          <p className="text-xl text-[#94a3b8] leading-relaxed max-w-2xl mb-12">
            Nuestra IA analiza probabilidades reales y las compara con las cuotas del mercado para identificar value bets que las casas subestiman. Está implementado para el <strong>fútbol internacional</strong> y <strong>La Liga</strong>.
          </p>
          
          <div className="flex flex-col sm:flex-row items-center gap-6">
            <Link href="/login" className="w-full sm:w-auto px-8 py-4 rounded-full bg-[#C0FF00] text-[#051209] font-bold text-lg hover:bg-[#a3d900] transition-colors shadow-[0_0_30px_rgba(192,255,0,0.3)] flex items-center justify-center gap-2">
              Comenzar <span className="text-xl">→</span>
            </Link>
            <a href="#producto" className="w-full sm:w-auto px-8 py-4 rounded-full border border-white/10 text-white font-bold text-lg hover:bg-white/5 transition-colors flex items-center justify-center gap-2">
              Ver ejemplo
            </a>
          </div>
        </div>

        {/* EL PROBLEMA */}
        <section className="mb-32">
          <div className="text-[10px] font-bold text-[#64748B] uppercase tracking-[0.2em] mb-4">El problema</div>
          <h2 className="text-3xl lg:text-4xl font-editorial font-bold mb-4">Las casas de apuestas no son infalibles</h2>
          <p className="text-[#94a3b8] max-w-2xl mb-12">
            Los modelos de las casas se equivocan sistemáticamente en ciertos tipos de partidos. Ahí está el valor.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white/5 border border-white/10 rounded-2xl p-8 hover:bg-white/10 transition-colors">
              <div className="w-10 h-10 bg-[#064E3B]/50 rounded-lg flex items-center justify-center text-[#C0FF00] mb-6">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path></svg>
              </div>
              <h3 className="text-lg font-bold mb-3">Favoritos excesivos</h3>
              <p className="text-sm text-[#94a3b8] leading-relaxed">
                Las casas sobrevaloran el factor local y subestiman equipos visitantes con mejor ranking.
              </p>
            </div>
            <div className="bg-white/5 border border-white/10 rounded-2xl p-8 hover:bg-white/10 transition-colors">
              <div className="w-10 h-10 bg-[#064E3B]/50 rounded-lg flex items-center justify-center text-[#C0FF00] mb-6">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              </div>
              <h3 className="text-lg font-bold mb-3">Sesgo de popularidad</h3>
              <p className="text-sm text-[#94a3b8] leading-relaxed">
                Los equipos mediáticos reciben cuotas infladas por el volumen de apuestas del público.
              </p>
            </div>
            <div className="bg-white/5 border border-white/10 rounded-2xl p-8 hover:bg-white/10 transition-colors">
              <div className="w-10 h-10 bg-[#064E3B]/50 rounded-lg flex items-center justify-center text-[#C0FF00] mb-6">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
              </div>
              <h3 className="text-lg font-bold mb-3">Datos desactualizados</h3>
              <p className="text-sm text-[#94a3b8] leading-relaxed">
                Los rankings Elo/FIFA y el estado de forma reciente no siempre se reflejan rápido en las cuotas.
              </p>
            </div>
          </div>
        </section>

        {/* PRODUCTO (EJEMPLO FIJO) */}
        <section id="producto" className="mb-32 pt-24 -mt-24">
          <div className="text-[10px] font-bold text-[#64748B] uppercase tracking-[0.2em] mb-4">Producto</div>
          <h2 className="text-3xl lg:text-4xl font-editorial font-bold mb-4">Así funciona una predicción</h2>
          <p className="text-[#94a3b8] max-w-2xl mb-12">
            Ejemplo real de una value bet identificada por el modelo en el Mundial 2022.
          </p>

          <div className="bg-[#0A1A12] border border-white/10 rounded-[2rem] p-8 lg:p-12 relative overflow-hidden">
            <div className="absolute top-8 right-8 flex gap-2">
              <span className="bg-[#064E3B]/30 border border-[#064E3B] text-[#C0FF00] px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-[#C0FF00] animate-pulse"></div>
                Value bet
              </span>
            </div>

            <div className="flex items-center gap-3 mb-2 pr-24 sm:pr-0">
              <span className="text-2xl font-editorial font-bold leading-tight">🇫🇷 Francia vs Marruecos 🇲🇦</span>
            </div>
            <div className="text-sm text-[#64748B] mb-6">Mundial 2022 · Semifinales · 14 dic, 20:00</div>

            <div className="flex gap-4 mb-10">
              <span className="px-3 py-1 rounded-md bg-white/5 border border-white/10 text-xs text-[#94a3b8]">Francia 1840 pts</span>
              <span className="px-3 py-1 rounded-md bg-white/5 border border-white/10 text-xs text-[#94a3b8]">Marruecos 1669 pts</span>
            </div>

            <div className="grid grid-cols-3 gap-8 mb-8 border-b border-white/10 pb-8">
              <div>
                <div className="text-xs text-[#64748B] uppercase tracking-widest mb-2">IA estima</div>
                <div className="text-xl font-bold text-white">Francia 61%</div>
              </div>
              <div>
                <div className="text-xs text-[#64748B] uppercase tracking-widest mb-2">Casa ofrece</div>
                <div className="text-xl font-bold text-white">Francia 48%</div>
              </div>
              <div>
                <div className="text-xs text-[#64748B] uppercase tracking-widest mb-2">Edge</div>
                <div className="text-xl font-bold text-[#C0FF00]">+13.0%</div>
              </div>
            </div>

            {/* Bars */}
            <div className="mb-10">
              <div className="flex h-3 rounded-full overflow-hidden bg-white/5 mb-3">
                <div className="bg-[#C0FF00]" style={{ width: '61%' }}></div>
                <div className="bg-[#64748B]" style={{ width: '21%' }}></div>
                <div className="bg-red-500" style={{ width: '18%' }}></div>
              </div>
              <div className="flex justify-between text-xs text-[#64748B] font-medium">
                <span>Francia 61%</span>
                <span>Empate 21%</span>
                <span>Marruecos 18%</span>
              </div>
            </div>

            <div className="flex justify-between items-center bg-white/5 rounded-2xl p-6 border border-white/10">
              <div className="flex gap-3">
                <span className="bg-[#064E3B]/20 text-[#C0FF00] px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest border border-[#064E3B]/30">
                  Riesgo Bajo
                </span>
                <span className="bg-[#064E3B]/30 text-[#C0FF00] px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest border border-[#064E3B]/50">
                  EV +8.4%
                </span>
              </div>
              <div className="text-right">
                <div className="text-xs text-[#64748B] uppercase tracking-widest mb-1">Cuota sugerida</div>
                <div className="text-2xl font-editorial font-bold text-white">2.08</div>
              </div>
            </div>
          </div>
        </section>

        {/* CÓMO FUNCIONA */}
        <section className="mb-32">
          <div className="text-[10px] font-bold text-[#64748B] uppercase tracking-[0.2em] mb-4">Cómo funciona</div>
          <h2 className="text-3xl lg:text-4xl font-editorial font-bold mb-4">Tres pasos para encontrar el valor</h2>
          <p className="text-[#94a3b8] max-w-2xl mb-12">
            El modelo analiza más de 25 variables por partido y las cruza con las cuotas del mercado en tiempo real.
          </p>

          <div className="space-y-8 relative before:absolute before:inset-y-0 before:left-6 before:w-px before:bg-gradient-to-b before:from-[#064E3B] before:to-transparent">
            <div className="relative pl-16">
              <div className="absolute left-0 top-0 w-12 h-12 rounded-full bg-[#051209] border border-[#064E3B] flex items-center justify-center text-[#C0FF00] font-bold z-10">1</div>
              <h3 className="text-xl font-bold mb-2">Análisis del partido</h3>
              <p className="text-[#94a3b8]">FIFA points, forma reciente, historial H2H, xG, posesión, calidad de plantilla y fase del torneo.</p>
            </div>
            <div className="relative pl-16">
              <div className="absolute left-0 top-0 w-12 h-12 rounded-full bg-[#051209] border border-[#064E3B] flex items-center justify-center text-[#C0FF00] font-bold z-10">2</div>
              <h3 className="text-xl font-bold mb-2">Cálculo de probabilidades reales</h3>
              <p className="text-[#94a3b8]">El modelo entrenado con datos históricos genera probabilidades 1X2 y O/U 2.5 calibradas de forma independiente a la casa de apuestas.</p>
            </div>
            <div className="relative pl-16">
              <div className="absolute left-0 top-0 w-12 h-12 rounded-full bg-[#051209] border border-[#064E3B] flex items-center justify-center text-[#C0FF00] font-bold z-10">3</div>
              <h3 className="text-xl font-bold mb-2">Detección del value</h3>
              <p className="text-[#94a3b8]">Compara nuestras predicciones con las cuotas de las principales casas. Si el edge supera el umbral dinámico, te llega la notificación de value bet.</p>
            </div>
          </div>
        </section>

        {/* RENDIMIENTO */}
        <section className="mb-32">
          <div className="text-[10px] font-bold text-[#64748B] uppercase tracking-[0.2em] mb-4">Rendimiento</div>
          <h2 className="text-3xl lg:text-4xl font-editorial font-bold mb-4">Resultados del último trimestre</h2>
          <p className="text-[#94a3b8] max-w-2xl mb-12">
            Basado en apuestas calificadas a stake fijo de 1 unidad.
          </p>

          <div className="bg-white/5 border border-white/10 rounded-3xl p-8 lg:p-12">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
              <div>
                <div className="text-4xl font-editorial font-bold text-white mb-2">85%</div>
                <div className="text-sm text-[#94a3b8]">Precisión riesgo bajo</div>
              </div>
              <div>
                <div className="text-4xl font-editorial font-bold text-white mb-2">70%</div>
                <div className="text-sm text-[#94a3b8]">Precisión riesgo medio</div>
              </div>
              <div>
                <div className="text-4xl font-editorial font-bold text-[#C0FF00] mb-2">+18%</div>
                <div className="text-sm text-[#94a3b8]">ROI promedio</div>
              </div>
              <div>
                <div className="text-4xl font-editorial font-bold text-white mb-2">247</div>
                <div className="text-sm text-[#94a3b8]">Apuestas analizadas</div>
              </div>
            </div>

            <div className="space-y-6">
              <div>
                <div className="flex justify-between text-sm font-medium mb-3">
                  <span className="text-white">Riesgo bajo</span>
                  <span className="text-[#C0FF00]">85%</span>
                </div>
                <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                  <div className="h-full bg-[#C0FF00] w-[85%] rounded-full shadow-[0_0_10px_rgba(192,255,0,0.5)]"></div>
                </div>
              </div>
              
              <div>
                <div className="flex justify-between text-sm font-medium mb-3">
                  <span className="text-white">Riesgo medio</span>
                  <span className="text-[#F59E0B]">70%</span>
                </div>
                <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                  <div className="h-full bg-[#F59E0B] w-[70%] rounded-full"></div>
                </div>
              </div>
              
              <div>
                <div className="flex justify-between text-sm font-medium mb-3">
                  <span className="text-white">Riesgo alto</span>
                  <span className="text-red-500">52%</span>
                </div>
                <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                  <div className="h-full bg-red-500 w-[52%] rounded-full"></div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* TESTIMONIOS */}
        <section className="mb-32">
          <div className="text-[10px] font-bold text-[#64748B] uppercase tracking-[0.2em] mb-4">Testimonios</div>
          <h2 className="text-3xl lg:text-4xl font-editorial font-bold mb-12">Lo que dicen los usuarios</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white/5 border border-white/10 rounded-2xl p-8 relative">
              <div className="text-[#C0FF00] text-5xl font-editorial absolute top-6 right-8 opacity-20">&quot;</div>
              <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 rounded-full bg-[#1A1C1E] flex items-center justify-center font-bold text-[#C0FF00]">
                  JM
                </div>
                <div>
                  <div className="font-bold text-white">Javier M.</div>
                  <div className="text-xs text-[#64748B]">Usuario Pro · 3 meses</div>
                </div>
              </div>
              <p className="text-[#94a3b8] italic relative z-10">
                &quot;Primera herramienta que me da contexto real detrás de cada predicción. El análisis de puntos Elo vs cuotas es lo que me faltaba.&quot;
              </p>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-2xl p-8 relative">
              <div className="text-[#C0FF00] text-5xl font-editorial absolute top-6 right-8 opacity-20">&quot;</div>
              <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 rounded-full bg-[#1A1C1E] flex items-center justify-center font-bold text-[#C0FF00]">
                  SR
                </div>
                <div>
                  <div className="font-bold text-white">Sara R.</div>
                  <div className="text-xs text-[#64748B]">Usuario Pro · 1 mes</div>
                </div>
              </div>
              <p className="text-[#94a3b8] italic relative z-10">
                &quot;Empecé a usar el sistema para La Liga y la diferencia es notable. El badge de riesgo es muy útil para gestionar mi bankroll de forma segura.&quot;
              </p>
            </div>
          </div>
        </section>

        {/* PRECIOS */}
        <section className="mb-32">
          <div className="text-center mb-16">
            <div className="text-[10px] font-bold text-[#64748B] uppercase tracking-[0.2em] mb-4">Precio</div>
            <h2 className="text-3xl lg:text-4xl font-editorial font-bold mb-4">Simple y transparente</h2>
          </div>

          <div className="max-w-md mx-auto">
            <div className="bg-gradient-to-b from-[#064E3B]/20 to-white/5 border border-[#064E3B]/50 rounded-[2rem] p-10 relative shadow-[0_0_50px_rgba(6,78,59,0.2)]">
              <div className="absolute top-0 right-10 -translate-y-1/2">
                <span className="bg-[#C0FF00] text-[#051209] px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest shadow-lg">
                  Más popular
                </span>
              </div>
              
              <div className="text-2xl font-editorial font-bold mb-2">Pro</div>
              <div className="flex items-baseline gap-1 mb-8">
                <span className="text-5xl font-bold text-white">9€</span>
                <span className="text-[#94a3b8]">/mes</span>
              </div>

              <ul className="space-y-4 mb-10">
                {[
                  'Predicciones ilimitadas',
                  'Cobertura 1X2 + O/U 2.5',
                  'Alertas value bet instantáneas',
                  'Análisis IA completo por partido',
                  'Fútbol: La Liga y Mundial'
                ].map((feature, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <svg className="w-5 h-5 text-[#C0FF00] shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                    <span className="text-[#94a3b8]">{feature}</span>
                  </li>
                ))}
              </ul>

              <Link href="/register" className="block w-full py-4 rounded-xl bg-[#C0FF00] text-[#051209] font-bold text-center hover:bg-[#a3d900] transition-colors shadow-[0_0_20px_rgba(192,255,0,0.2)]">
                Empezar ahora
              </Link>
            </div>
          </div>
        </section>

        {/* PREGUNTAS FRECUENTES */}
        <section className="mb-16">
          <div className="text-[10px] font-bold text-[#64748B] uppercase tracking-[0.2em] mb-4">Preguntas frecuentes</div>
          <h2 className="text-3xl lg:text-4xl font-editorial font-bold mb-12">Resuelve tus dudas</h2>

          <div className="space-y-6">
            <div className="border-t border-white/10 pt-6">
              <h3 className="text-lg font-bold mb-2 text-white">¿El modelo garantiza ganancias?</h3>
              <p className="text-[#94a3b8] leading-relaxed text-sm">
                No. El modelo identifica value bets estadísticamente favorables, pero las apuestas deportivas conllevan riesgo. El objetivo es tener edge a largo plazo, no ganar cada apuesta.
              </p>
            </div>
            <div className="border-t border-white/10 pt-6">
              <h3 className="text-lg font-bold mb-2 text-white">¿Con qué deportes funciona?</h3>
              <p className="text-[#94a3b8] leading-relaxed text-sm">
                Actualmente especializado en fútbol de selecciones nacionales (Copa del Mundo, Eurocopas, Nations League) y en La Liga española.
              </p>
            </div>
            <div className="border-t border-white/10 pt-6">
              <h3 className="text-lg font-bold mb-2 text-white">¿Cada cuánto se actualiza el modelo?</h3>
              <p className="text-[#94a3b8] leading-relaxed text-sm">
                El modelo se reentrena automáticamente después de cada ventana de partidos con los resultados más recientes. Los FIFA points se actualizan mensualmente.
              </p>
            </div>
            <div className="border-t border-white/10 pt-6">
              <h3 className="text-lg font-bold mb-2 text-white">¿Puedo cancelar en cualquier momento?</h3>
              <p className="text-[#94a3b8] leading-relaxed text-sm">
                Sí, sin permanencia ni penalización. Cancela desde tu perfil y seguirás teniendo acceso hasta el fin del período pagado.
              </p>
            </div>
          </div>
        </section>

      </main>

      <footer className="border-t border-white/5 bg-[#051209] py-12 text-center text-sm text-[#64748B]">
        <div className="mb-4 text-xl font-editorial font-bold text-white">
          ValueBet AI<span className="text-[#C0FF00]">.</span>
        </div>
        <p>© 2026 ValueBet AI. Todos los derechos reservados.</p>
      </footer>
    </div>
  );
}
