import Link from 'next/link';
import Image from 'next/image';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 font-sans selection:bg-[#C8A252]/30 selection:text-[#1B365D] overflow-x-hidden relative">
      
      {/* Background elements */}
      <div className="fixed top-0 left-0 w-full h-[800px] bg-gradient-to-b from-[#5885A8]/10 to-transparent pointer-events-none" />
      <div className="fixed -top-[20%] -right-[10%] w-[70vw] h-[70vw] rounded-full bg-[#C8A252]/[0.05] blur-[120px] pointer-events-none" />
      
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 px-8 py-6 flex justify-between items-center backdrop-blur-md bg-[#F8FAFC]/80 border-b border-slate-200">
        <Link href="/" className="flex items-center"><Image src="/logo.png" alt="QuantStake Logo" width={220} height={60} className="h-12 w-auto object-contain" priority /></Link>
        <div className="flex gap-4">
          <Link href="/login" className="px-5 py-2.5 rounded-full text-sm font-bold text-slate-600 hover:text-slate-900 transition-colors">
            Iniciar sesión
          </Link>
          <Link href="/register" className="px-5 py-2.5 rounded-full text-sm font-bold bg-[#1B365D] text-white hover:bg-[#132845] transition-colors shadow-md">
            Comenzar
          </Link>
        </div>
      </nav>

      <main className="relative z-10 pt-32 lg:pt-40 pb-24 max-w-5xl mx-auto px-8">
        
        {/* HERO SECTION */}
        <div className="mb-32">
          <div className="inline-flex items-center gap-2 bg-[#E2E8F0] border border-slate-300 text-[#1B365D] px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest mb-6">
            <div className="w-1.5 h-1.5 rounded-full bg-[#1B365D] animate-pulse"></div>
            La Liga 2026/27 · En curso
          </div>
          
          <h1 className="text-4xl lg:text-6xl font-editorial font-bold leading-[1.1] mb-8 text-balance">
            Sistema de <i className="text-slate-600 font-normal">Inteligencia Artificial</i> para detectar cuotas rentables en tiempo real.
          </h1>
          
          <p className="text-xl text-slate-600 leading-relaxed max-w-2xl mb-12">
            Nuestra IA analiza probabilidades reales y las compara con las cuotas del mercado para identificar value bets que las casas subestiman. Especializado en <strong>La Liga</strong> y otras competiciones de élite.
          </p>
          
          <div className="flex flex-col sm:flex-row items-center gap-6">
            <Link href="/register" className="w-full sm:w-auto px-8 py-4 rounded-full bg-[#1B365D] text-white font-bold text-lg hover:bg-[#132845] transition-colors shadow-lg shadow-[#1B365D]/20 flex items-center justify-center gap-2">
              Empezar gratis <span className="text-xl">→</span>
            </Link>
            <a href="#producto" className="w-full sm:w-auto px-8 py-4 rounded-full border border-slate-200 text-slate-900 font-bold text-lg hover:bg-slate-100 transition-colors flex items-center justify-center gap-2">
              Ver ejemplo
            </a>
          </div>
        </div>

        {/* EL PROBLEMA */}
        <section className="mb-32">
          <div className="text-[10px] font-bold text-[#C8A252] uppercase tracking-[0.2em] mb-4">El problema</div>
          <h2 className="text-3xl lg:text-4xl font-editorial font-bold mb-4">Las casas de apuestas no son infalibles</h2>
          <p className="text-slate-600 max-w-2xl mb-12">
            Los modelos de las casas se equivocan sistemáticamente en ciertos tipos de partidos. Ahí está el valor.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white border border-slate-200 rounded-2xl p-8 hover:shadow-md transition-shadow transition-colors">
              <div className="w-10 h-10 bg-[#F1F5F9] rounded-lg flex items-center justify-center text-[#1B365D] mb-6">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path></svg>
              </div>
              <h3 className="text-lg font-bold mb-3">Favoritos excesivos</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Las casas sobrevaloran el factor local y subestiman equipos visitantes con mejor ranking.
              </p>
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl p-8 hover:shadow-md transition-shadow transition-colors">
              <div className="w-10 h-10 bg-[#F1F5F9] rounded-lg flex items-center justify-center text-[#1B365D] mb-6">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              </div>
              <h3 className="text-lg font-bold mb-3">Sesgo de popularidad</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Los equipos mediáticos reciben cuotas infladas por el volumen de apuestas del público.
              </p>
            </div>
            <div className="bg-white border border-slate-200 rounded-2xl p-8 hover:shadow-md transition-shadow transition-colors">
              <div className="w-10 h-10 bg-[#F1F5F9] rounded-lg flex items-center justify-center text-[#1B365D] mb-6">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
              </div>
              <h3 className="text-lg font-bold mb-3">Datos desactualizados</h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Los rankings Elo/FIFA y el estado de forma reciente no siempre se reflejan rápido en las cuotas.
              </p>
            </div>
          </div>
        </section>

        {/* PRODUCTO (EJEMPLO FIJO) */}
        <section id="producto" className="mb-32 pt-24 -mt-24">
          <div className="text-[10px] font-bold text-[#C8A252] uppercase tracking-[0.2em] mb-4">Producto</div>
          <h2 className="text-3xl lg:text-4xl font-editorial font-bold mb-4">Así funciona una predicción</h2>
          <p className="text-slate-600 max-w-2xl mb-12">
            Ejemplo real de una value bet identificada por el modelo en La Liga 2024/25.
          </p>

          <div className="bg-white shadow-xl border border-slate-200 rounded-[2rem] p-8 lg:p-12 relative overflow-hidden">
            <div className="absolute top-8 right-8 flex gap-2">
              <span className="bg-[#E2E8F0] border border-slate-300 text-[#1B365D] px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-[#1B365D] animate-pulse"></div>
                Value bet
              </span>
            </div>

            <div className="flex items-center gap-3 mb-2 pr-24 sm:pr-0">
              <span className="text-2xl font-editorial font-bold leading-tight">🔴 Real Madrid vs Atlético de Madrid 🔴</span>
            </div>
            <div className="text-sm text-[#64748B] mb-6">La Liga 2024/25 · Jornada 28 · 9 mar, 21:00</div>

            <div className="flex gap-4 mb-10">
              <span className="px-3 py-1 rounded-md bg-white border border-slate-200 text-xs text-slate-600">Real Madrid Elo 2030 pts</span>
              <span className="px-3 py-1 rounded-md bg-white border border-slate-200 text-xs text-slate-600">Atlético Elo 1940 pts</span>
            </div>

            <div className="grid grid-cols-3 gap-8 mb-8 border-b border-slate-200 pb-8">
              <div>
                <div className="text-xs text-[#64748B] uppercase tracking-widest mb-2">IA estima</div>
                <div className="text-xl font-bold text-slate-900">Real Madrid 55%</div>
              </div>
              <div>
                <div className="text-xs text-[#64748B] uppercase tracking-widest mb-2">Casa ofrece</div>
                <div className="text-xl font-bold text-slate-900">Real Madrid 44%</div>
              </div>
              <div>
                <div className="text-xs text-[#64748B] uppercase tracking-widest mb-2">Edge</div>
                <div className="text-xl font-bold text-[#1B365D]">+11.0%</div>
              </div>
            </div>

            {/* Bars */}
            <div className="mb-10">
              <div className="flex h-3 rounded-full overflow-hidden bg-white mb-3">
                <div className="bg-[#1B365D]" style={{ width: '55%' }}></div>
                <div className="bg-[#64748B]" style={{ width: '25%' }}></div>
                <div className="bg-red-500" style={{ width: '20%' }}></div>
              </div>
              <div className="flex justify-between text-xs text-[#64748B] font-medium">
                <span>Real Madrid 55%</span>
                <span>Empate 25%</span>
                <span>Atlético 20%</span>
              </div>
            </div>

            <div className="flex justify-between items-center bg-white rounded-2xl p-6 border border-slate-200">
              <div className="flex gap-3">
                <span className="bg-[#064E3B]/20 text-[#1B365D] px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest border border-slate-300/30">
                  Riesgo Bajo
                </span>
                <span className="bg-[#E2E8F0] text-[#1B365D] px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest border border-slate-300/50">
                  EV +7.2%
                </span>
              </div>
              <div className="text-right">
                <div className="text-xs text-[#64748B] uppercase tracking-widest mb-1">Cuota sugerida</div>
                <div className="text-2xl font-editorial font-bold text-slate-900">2.27</div>
              </div>
            </div>
          </div>
        </section>

        {/* CÓMO FUNCIONA */}
        <section className="mb-32">
          <div className="text-[10px] font-bold text-[#C8A252] uppercase tracking-[0.2em] mb-4">Cómo funciona</div>
          <h2 className="text-3xl lg:text-4xl font-editorial font-bold mb-4">Tres pasos para encontrar el valor</h2>
          <p className="text-slate-600 max-w-2xl mb-12">
            El modelo analiza más de 25 variables por partido y las cruza con las cuotas del mercado en tiempo real.
          </p>

          <div className="space-y-8 relative before:absolute before:inset-y-0 before:left-6 before:w-px before:bg-gradient-to-b before:from-[#064E3B] before:to-transparent">
            <div className="relative pl-16">
              <div className="absolute left-0 top-0 w-12 h-12 rounded-full bg-[#F8FAFC] border border-slate-300 flex items-center justify-center text-[#1B365D] font-bold z-10">1</div>
              <h3 className="text-xl font-bold mb-2">Análisis del partido</h3>
              <p className="text-slate-600">Elo clubes, forma reciente, historial H2H, xG, posesión, calidad de plantilla y contexto de la jornada.</p>
            </div>
            <div className="relative pl-16">
              <div className="absolute left-0 top-0 w-12 h-12 rounded-full bg-[#F8FAFC] border border-slate-300 flex items-center justify-center text-[#1B365D] font-bold z-10">2</div>
              <h3 className="text-xl font-bold mb-2">Cálculo de probabilidades reales</h3>
              <p className="text-slate-600">El modelo entrenado con datos históricos genera probabilidades 1X2 y O/U 2.5 calibradas de forma independiente a la casa de apuestas.</p>
            </div>
            <div className="relative pl-16">
              <div className="absolute left-0 top-0 w-12 h-12 rounded-full bg-[#F8FAFC] border border-slate-300 flex items-center justify-center text-[#1B365D] font-bold z-10">3</div>
              <h3 className="text-xl font-bold mb-2">Detección del value</h3>
              <p className="text-slate-600">Compara nuestras predicciones con las cuotas de las principales casas. Si el edge supera el umbral dinámico, te llega la notificación de value bet.</p>
            </div>
          </div>
        </section>

        {/* RENDIMIENTO */}
        <section className="mb-32">
          <div className="text-[10px] font-bold text-[#C8A252] uppercase tracking-[0.2em] mb-4">Rendimiento</div>
          <h2 className="text-3xl lg:text-4xl font-editorial font-bold mb-4">Resultados del último trimestre</h2>
          <p className="text-slate-600 max-w-2xl mb-12">
            Basado en apuestas calificadas a stake fijo de 1 unidad.
          </p>

          <div className="bg-white border border-slate-200 rounded-3xl p-8 lg:p-12">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
              <div>
                <div className="text-4xl font-editorial font-bold text-slate-900 mb-2">85%</div>
                <div className="text-sm text-slate-600">Precisión riesgo bajo</div>
              </div>
              <div>
                <div className="text-4xl font-editorial font-bold text-slate-900 mb-2">70%</div>
                <div className="text-sm text-slate-600">Precisión riesgo medio</div>
              </div>
              <div>
                <div className="text-4xl font-editorial font-bold text-[#1B365D] mb-2">+18%</div>
                <div className="text-sm text-slate-600">ROI promedio</div>
              </div>
              <div>
                <div className="text-4xl font-editorial font-bold text-slate-900 mb-2">247</div>
                <div className="text-sm text-slate-600">Apuestas analizadas</div>
              </div>
            </div>

            <div className="space-y-6">
              <div>
                <div className="flex justify-between text-sm font-medium mb-3">
                  <span className="text-slate-900">Riesgo bajo</span>
                  <span className="text-[#1B365D]">85%</span>
                </div>
                <div className="h-2 w-full bg-white rounded-full overflow-hidden">
                  <div className="h-full bg-[#1B365D] w-[85%] rounded-full shadow-[0_0_10px_rgba(192,255,0,0.5)]"></div>
                </div>
              </div>
              
              <div>
                <div className="flex justify-between text-sm font-medium mb-3">
                  <span className="text-slate-900">Riesgo medio</span>
                  <span className="text-[#F59E0B]">70%</span>
                </div>
                <div className="h-2 w-full bg-white rounded-full overflow-hidden">
                  <div className="h-full bg-[#F59E0B] w-[70%] rounded-full"></div>
                </div>
              </div>
              
              <div>
                <div className="flex justify-between text-sm font-medium mb-3">
                  <span className="text-slate-900">Riesgo alto</span>
                  <span className="text-red-500">52%</span>
                </div>
                <div className="h-2 w-full bg-white rounded-full overflow-hidden">
                  <div className="h-full bg-red-500 w-[52%] rounded-full"></div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* TESTIMONIOS */}
        <section className="mb-32">
          <div className="text-[10px] font-bold text-[#C8A252] uppercase tracking-[0.2em] mb-4">Testimonios</div>
          <h2 className="text-3xl lg:text-4xl font-editorial font-bold mb-12">Lo que dicen los usuarios</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white border border-slate-200 rounded-2xl p-8 relative">
              <div className="text-[#1B365D] text-5xl font-editorial absolute top-6 right-8 opacity-20">&quot;</div>
              <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 rounded-full bg-[#1A1C1E] flex items-center justify-center font-bold text-[#1B365D]">
                  JM
                </div>
                <div>
                  <div className="font-bold text-slate-900">Javier M.</div>
                  <div className="text-xs text-[#64748B]">Usuario Pro · 3 meses</div>
                </div>
              </div>
              <p className="text-slate-600 italic relative z-10">
                &quot;Primera herramienta que me da contexto real detrás de cada predicción. El análisis de puntos Elo vs cuotas es lo que me faltaba.&quot;
              </p>
            </div>

            <div className="bg-white border border-slate-200 rounded-2xl p-8 relative">
              <div className="text-[#1B365D] text-5xl font-editorial absolute top-6 right-8 opacity-20">&quot;</div>
              <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 rounded-full bg-[#1A1C1E] flex items-center justify-center font-bold text-[#1B365D]">
                  SR
                </div>
                <div>
                  <div className="font-bold text-slate-900">Sara R.</div>
                  <div className="text-xs text-[#64748B]">Usuario Pro · 1 mes</div>
                </div>
              </div>
              <p className="text-slate-600 italic relative z-10">
                &quot;Empecé a usar el sistema para La Liga y la diferencia es notable. El badge de riesgo es muy útil para gestionar mi bankroll de forma segura.&quot;
              </p>
            </div>
          </div>
        </section>

        {/* PRECIOS */}
        <section className="mb-32">
          <div className="text-center mb-16">
            <div className="text-[10px] font-bold text-[#C8A252] uppercase tracking-[0.2em] mb-4">Precio</div>
            <h2 className="text-3xl lg:text-4xl font-editorial font-bold mb-4">Simple y transparente</h2>
          </div>

          <div className="max-w-md mx-auto">
            <div className="bg-gradient-to-b from-[#5885A8]/10 to-white/5 border border-slate-300/50 rounded-[2rem] p-10 relative shadow-[0_0_50px_rgba(6,78,59,0.2)]">
              <div className="absolute top-0 right-10 -translate-y-1/2">
                <span className="bg-[#1B365D] text-white px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest shadow-lg">
                  Más popular
                </span>
              </div>
              
              <div className="text-2xl font-editorial font-bold mb-2">Pro</div>

              {/* 7-day trial banner */}
              <div className="flex items-center gap-2 bg-[#064E3B]/40 border border-slate-300 rounded-xl px-4 py-3 mb-6">
                <div className="w-2 h-2 rounded-full bg-[#1B365D] animate-pulse shrink-0" />
                <div>
                  <p className="text-[#1B365D] text-xs font-black uppercase tracking-widest">7 días GRATIS</p>
                  <p className="text-slate-600 text-[11px] mt-0.5">Después, 9,99€/mes. Cancela cuando quieras.</p>
                </div>
              </div>

              <div className="flex items-baseline gap-1 mb-8">
                <span className="text-5xl font-bold text-slate-900">9,99€</span>
                <span className="text-slate-600">/mes</span>
              </div>

              <ul className="space-y-4 mb-10">
                {[
                  'Predicciones ilimitadas',
                  'Cobertura 1X2 + O/U 2.5',
                  'Alertas value bet instantáneas',
                  'Análisis IA completo por partido',
                  'La Liga en exclusiva'
                ].map((feature, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <svg className="w-5 h-5 text-[#1B365D] shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                    <span className="text-slate-600">{feature}</span>
                  </li>
                ))}
              </ul>

              <Link href="/register" className="block w-full py-4 rounded-xl bg-[#1B365D] text-white font-bold text-center hover:bg-[#132845] transition-colors shadow-md">
                Empezar 7 días gratis
              </Link>
              <p className="text-center text-[#64748B] text-[10px] mt-3">Sin compromiso. Sin permanencia.</p>
            </div>
          </div>
        </section>

        {/* PREGUNTAS FRECUENTES */}
        <section className="mb-16">
          <div className="text-[10px] font-bold text-[#C8A252] uppercase tracking-[0.2em] mb-4">Preguntas frecuentes</div>
          <h2 className="text-3xl lg:text-4xl font-editorial font-bold mb-12">Resuelve tus dudas</h2>

          <div className="space-y-6">
            <div className="border-t border-slate-200 pt-6">
              <h3 className="text-lg font-bold mb-2 text-slate-900">¿Debes apostar a todas las cuotas que el sistema marque como value bets?</h3>
              <p className="text-slate-600 leading-relaxed text-sm">
                No, una value bet es que hay más probabilidad real de que ocurra de lo que cree la casa de apuestas, sin embargo puede que haya muy poca probabildad de que ocurra. Por tanto se debe de usar para analizar el mercado y analizar riesgos. Nuestro sistema califica las value bets según si nivel de riesgo como bajo, medio, alto o lotería.
              </p>
            </div>
            <div className="border-t border-slate-200 pt-6">
              <h3 className="text-lg font-bold mb-2 text-slate-900">¿El modelo garantiza ganancias?</h3>
              <p className="text-slate-600 leading-relaxed text-sm">
                No. El modelo identifica value bets estadísticamente favorables, pero las apuestas deportivas conllevan riesgo. El objetivo es tener edge a largo plazo, no ganar cada apuesta.
              </p>
            </div>
            <div className="border-t border-slate-200 pt-6">
              <h3 className="text-lg font-bold mb-2 text-slate-900">¿Con qué deportes funciona?</h3>
              <p className="text-slate-600 leading-relaxed text-sm">
                Actualmente especializado en fútbol de clubes (La Liga española) y selección (Copa del Mundo, Eurocopas, Nations League).
              </p>
            </div>
            <div className="border-t border-slate-200 pt-6">
              <h3 className="text-lg font-bold mb-2 text-slate-900">¿Cada cuánto se actualiza el modelo?</h3>
              <p className="text-slate-600 leading-relaxed text-sm">
                El modelo se reentrena automáticamente después de cada jornada con los resultados más recientes. Los datos Elo de clubes se actualizan semanalmente.
              </p>
            </div>
            <div className="border-t border-slate-200 pt-6">
              <h3 className="text-lg font-bold mb-2 text-slate-900">¿Cómo funciona la prueba gratuita de 7 días?</h3>
              <p className="text-slate-600 leading-relaxed text-sm">
                Al registrarte, obtienes acceso completo a todas las funcionalidades durante 7 días sin cargo alguno. Al finalizar el período de prueba, tu suscripción se renueva automáticamente por 9,99€/mes. Puedes cancelar en cualquier momento antes de que acabe la prueba y no se te cobrará nada.
              </p>
            </div>
            <div className="border-t border-slate-200 pt-6">
              <h3 className="text-lg font-bold mb-2 text-slate-900">¿Puedo cancelar en cualquier momento?</h3>
              <p className="text-slate-600 leading-relaxed text-sm">
                Sí, sin permanencia ni penalización. Cancela desde tu perfil y seguirás teniendo acceso hasta el fin del período pagado.
              </p>
            </div>
          </div>
        </section>

      </main>

      <footer className="border-t border-slate-200 bg-[#F8FAFC] py-12 text-center text-sm text-[#64748B] px-6">
        <div className="max-w-4xl mx-auto flex flex-col items-center">
          <div className="mb-4 text-xl font-editorial font-bold text-slate-900">
            QuantStake<span className="text-[#1B365D]">.</span>
          </div>
          
          <div className="mb-6 space-y-2 text-xs text-[#64748B]/70 max-w-3xl">
            <p>
              <strong className="text-[#64748B]">Descargo de responsabilidad:</strong> QuantStake es una herramienta de análisis estadístico e información deportiva. No somos una casa de apuestas, no organizamos juegos de azar ni gestionamos fondos de terceros. 
            </p>
            <p>
              Las apuestas deportivas conllevan un alto riesgo económico y pueden causar adicción. No garantizamos rentabilidades futuras ni nos hacemos responsables de posibles pérdidas económicas derivadas del uso de nuestra plataforma. Utiliza esta información únicamente con fines orientativos.
            </p>
            <p className="font-semibold text-slate-600">
              Juega con responsabilidad. +18
            </p>
          </div>

          <div className="flex gap-4 mb-8 text-xs underline decoration-white/20 underline-offset-4">
            <a href="/terminos" className="hover:text-slate-900 transition-colors">Términos y Condiciones</a>
            <a href="/privacidad" className="hover:text-slate-900 transition-colors">Política de Privacidad</a>
            <a href="/cookies" className="hover:text-slate-900 transition-colors">Política de Cookies</a>
          </div>

          <p>© 2026 QuantStake. Todos los derechos reservados.</p>
        </div>
      </footer>
    </div>
  );
}
