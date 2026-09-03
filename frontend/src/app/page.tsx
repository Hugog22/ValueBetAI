import Link from 'next/link';
import Image from 'next/image';

// ─── Inline SVG helpers ────────────────────────────────────────────────────
const CheckIcon = () => (
  <svg className="w-5 h-5 text-[#C8A252] shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
  </svg>
);

const StarIcon = () => (
  <svg className="w-4 h-4 fill-[#C8A252] text-[#C8A252]" viewBox="0 0 20 20">
    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
  </svg>
);

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#0D1117] text-white font-sans overflow-x-hidden">

      {/* ── Subtle grid background ── */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          backgroundImage: `
            linear-gradient(rgba(200,162,82,0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(200,162,82,0.04) 1px, transparent 1px)
          `,
          backgroundSize: '60px 60px',
        }}
      />
      {/* Glow top-right */}
      <div className="fixed top-0 right-0 w-[800px] h-[600px] bg-[#1B365D]/20 rounded-full blur-[120px] pointer-events-none -translate-y-1/2 translate-x-1/3" />
      {/* Glow bottom-left */}
      <div className="fixed bottom-0 left-0 w-[600px] h-[400px] bg-[#C8A252]/8 rounded-full blur-[100px] pointer-events-none translate-y-1/2 -translate-x-1/4" />

      {/* ══════════════════════════════════════════════════════════════
           NAV
      ══════════════════════════════════════════════════════════════ */}
      <nav className="fixed top-0 left-0 right-0 z-50 px-6 lg:px-12 py-4 flex justify-between items-center border-b border-white/[0.06] bg-[#0D1117]/80 backdrop-blur-xl">
        <Link href="/" className="flex items-center">
          <Image src="/logo.png" alt="QuantStake" width={180} height={48} className="h-10 w-auto object-contain brightness-0 invert" priority />
        </Link>

        <div className="hidden md:flex items-center gap-8 text-sm font-medium text-white/60">
          <a href="#como-funciona" className="hover:text-white transition-colors">Cómo funciona</a>
          <a href="#rendimiento" className="hover:text-white transition-colors">Rendimiento</a>
          <a href="#precios" className="hover:text-white transition-colors">Precios</a>
          <a href="#faq" className="hover:text-white transition-colors">FAQ</a>
        </div>

        <div className="flex items-center gap-3">
          <Link href="/login" className="hidden sm:block px-4 py-2 text-sm font-semibold text-white/70 hover:text-white transition-colors">
            Iniciar sesión
          </Link>
          <Link
            href="/register"
            className="px-5 py-2.5 rounded-full text-sm font-bold bg-[#C8A252] text-[#0D1117] hover:bg-[#d4b06a] transition-all shadow-[0_0_20px_rgba(200,162,82,0.25)]"
          >
            Empezar gratis →
          </Link>
        </div>
      </nav>

      {/* ══════════════════════════════════════════════════════════════
           HERO
      ══════════════════════════════════════════════════════════════ */}
      <section className="relative z-10 pt-36 lg:pt-44 pb-24 px-6 lg:px-12 max-w-6xl mx-auto">

        {/* Trust badge */}
        <div className="flex justify-center mb-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-[#C8A252]/30 bg-[#C8A252]/10 text-[#C8A252] text-xs font-bold uppercase tracking-widest">
            <span className="w-1.5 h-1.5 rounded-full bg-[#C8A252] animate-pulse" />
            La Liga 2026/27 · Análisis en tiempo real
          </div>
        </div>

        <h1 className="text-center text-5xl lg:text-7xl font-bold leading-[1.05] mb-6 tracking-tight">
          Encuentra el{' '}
          <span className="relative inline-block">
            <span className="text-[#C8A252]">edge</span>
          </span>
          {' '}antes{' '}
          <br className="hidden lg:block" />
          que las casas lo corrijan
        </h1>

        <p className="text-center text-lg lg:text-xl text-white/60 max-w-2xl mx-auto mb-10 leading-relaxed">
          QuantStake es un sistema de análisis cuantitativo que compara probabilidades reales calculadas por IA con las cuotas del mercado, detectando ineficiencias antes de que desaparezcan.
        </p>

        {/* Social proof row */}
        <div className="flex justify-center items-center gap-6 mb-10 text-sm text-white/50">
          <div className="flex items-center gap-1.5">
            <div className="flex">
              {[1,2,3,4,5].map(i => <StarIcon key={i} />)}
            </div>
            <span className="text-white/60 font-medium">4.8/5</span>
          </div>
          <span className="w-px h-4 bg-white/20" />
          <span>+500 usuarios activos</span>
          <span className="w-px h-4 bg-white/20" />
          <span>247 apuestas analizadas este trimestre</span>
        </div>

        <div className="flex flex-col sm:flex-row justify-center gap-4 mb-16">
          <Link
            href="/register"
            className="px-8 py-4 rounded-full bg-[#C8A252] text-[#0D1117] font-bold text-base hover:bg-[#d4b06a] transition-all shadow-[0_0_40px_rgba(200,162,82,0.3)] flex items-center justify-center gap-2"
          >
            Prueba 7 días gratis
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M9 5l7 7-7 7" />
            </svg>
          </Link>
          <a
            href="#demo"
            className="px-8 py-4 rounded-full border border-white/15 text-white font-bold text-base hover:bg-white/5 transition-all flex items-center justify-center gap-2"
          >
            Ver ejemplo real
          </a>
        </div>

        {/* ── Live prediction card demo ── */}
        <div id="demo" className="relative max-w-3xl mx-auto">
          {/* Card glow */}
          <div className="absolute inset-0 bg-gradient-to-b from-[#C8A252]/15 to-[#1B365D]/10 rounded-3xl blur-2xl" />
          <div className="relative bg-[#161B22] border border-white/10 rounded-3xl p-6 lg:p-10 overflow-hidden">

            {/* Card header */}
            <div className="flex items-start justify-between mb-6">
              <div>
                <p className="text-white/40 text-xs uppercase tracking-widest mb-1">La Liga 2024/25 · Jornada 28</p>
                <h3 className="text-xl lg:text-2xl font-bold">Real Madrid vs Atlético de Madrid</h3>
                <p className="text-white/40 text-sm mt-1">9 mar 2025 · 21:00 h</p>
              </div>
              <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#C8A252]/15 border border-[#C8A252]/30 text-[#C8A252] text-xs font-bold uppercase tracking-wider">
                <span className="w-1.5 h-1.5 rounded-full bg-[#C8A252] animate-pulse" />
                Value Bet
              </span>
            </div>

            {/* Stats grid */}
            <div className="grid grid-cols-3 gap-4 mb-6 p-5 rounded-2xl bg-white/[0.04] border border-white/[0.06]">
              <div>
                <p className="text-white/40 text-[10px] uppercase tracking-widest mb-1">IA estima</p>
                <p className="text-xl font-bold text-white">55.2%</p>
                <p className="text-white/40 text-xs">victoria local</p>
              </div>
              <div>
                <p className="text-white/40 text-[10px] uppercase tracking-widest mb-1">Casa ofrece</p>
                <p className="text-xl font-bold text-white">44.1%</p>
                <p className="text-white/40 text-xs">implícito</p>
              </div>
              <div>
                <p className="text-white/40 text-[10px] uppercase tracking-widest mb-1">Edge</p>
                <p className="text-xl font-bold text-[#C8A252]">+11.1%</p>
                <p className="text-white/40 text-xs">favorable</p>
              </div>
            </div>

            {/* Probability bar */}
            <div className="mb-6">
              <div className="flex h-2.5 rounded-full overflow-hidden bg-white/[0.06] mb-2">
                <div className="bg-[#C8A252] rounded-l-full" style={{ width: '55%' }} />
                <div className="bg-white/30" style={{ width: '25%' }} />
                <div className="bg-[#1B365D] rounded-r-full" style={{ width: '20%' }} />
              </div>
              <div className="flex justify-between text-xs text-white/40">
                <span>Real Madrid 55%</span>
                <span>Empate 25%</span>
                <span>Atlético 20%</span>
              </div>
            </div>

            {/* Bottom row */}
            <div className="flex items-center justify-between pt-4 border-t border-white/[0.06]">
              <div className="flex gap-2">
                <span className="px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/20 text-emerald-400 text-xs font-bold uppercase tracking-wider">Riesgo Bajo</span>
                <span className="px-3 py-1 rounded-full bg-[#C8A252]/15 border border-[#C8A252]/20 text-[#C8A252] text-xs font-bold uppercase tracking-wider">EV +7.2%</span>
              </div>
              <div className="text-right">
                <p className="text-white/40 text-[10px] uppercase tracking-widest">Cuota sugerida</p>
                <p className="text-2xl font-bold">2.27</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
           LOGOS / TRUST BAR
      ══════════════════════════════════════════════════════════════ */}
      <section className="relative z-10 py-12 border-y border-white/[0.06]">
        <div className="max-w-5xl mx-auto px-6 text-center">
          <p className="text-white/30 text-xs uppercase tracking-[0.25em] mb-8 font-semibold">Compatible con cuotas de</p>
          <div className="flex flex-wrap justify-center gap-8 lg:gap-14 items-center text-white/25 text-sm font-bold uppercase tracking-widest">
            <span>Bet365</span>
            <span className="w-px h-4 bg-white/10" />
            <span>Betfair</span>
            <span className="w-px h-4 bg-white/10" />
            <span>Pinnacle</span>
            <span className="w-px h-4 bg-white/10" />
            <span>William Hill</span>
            <span className="w-px h-4 bg-white/10" />
            <span>1xBet</span>
            <span className="w-px h-4 bg-white/10" />
            <span>Unibet</span>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
           PROBLEMA / AGITACIÓN
      ══════════════════════════════════════════════════════════════ */}
      <section className="relative z-10 py-28 px-6 lg:px-12 max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <p className="text-[#C8A252] text-xs font-bold uppercase tracking-[0.25em] mb-4">El problema</p>
          <h2 className="text-4xl lg:text-5xl font-bold leading-tight mb-6">
            Las casas ganan porque tienen<br className="hidden lg:block" /> mejores datos que tú.
          </h2>
          <p className="text-white/50 max-w-xl mx-auto text-lg">Hasta ahora. QuantStake nivela el campo de juego.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            {
              icon: (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
              ),
              title: 'Cuotas con margen oculto',
              desc: 'Las casas integran un margen del 5-8% en cada cuota, haciendo imposible ganar a largo plazo sin detectar dónde se equivocan.',
            },
            {
              icon: (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
              ),
              title: 'Sesgo de popularidad',
              desc: 'El dinero del público deforma las cuotas de equipos mediáticos como el Real Madrid, creando ineficiencias que el modelo identifica.',
            },
            {
              icon: (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              ),
              title: 'Ventanas de valor cortas',
              desc: 'Las ineficiencias duran horas. Cuando las casas ajustan la cuota, la oportunidad desaparece. Velocidad y datos son clave.',
            },
          ].map(({ icon, title, desc }) => (
            <div key={title} className="p-8 rounded-2xl bg-[#161B22] border border-white/[0.07] hover:border-[#C8A252]/20 transition-all group">
              <div className="w-12 h-12 rounded-xl bg-[#C8A252]/10 flex items-center justify-center text-[#C8A252] mb-5 group-hover:bg-[#C8A252]/15 transition-colors">
                {icon}
              </div>
              <h3 className="font-bold text-lg mb-3 text-white">{title}</h3>
              <p className="text-white/50 text-sm leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
           CÓMO FUNCIONA
      ══════════════════════════════════════════════════════════════ */}
      <section id="como-funciona" className="relative z-10 py-28 px-6 lg:px-12 max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <p className="text-[#C8A252] text-xs font-bold uppercase tracking-[0.25em] mb-4">Metodología</p>
          <h2 className="text-4xl lg:text-5xl font-bold leading-tight mb-6">Ciencia detrás de cada predicción</h2>
          <p className="text-white/50 max-w-2xl mx-auto">
            Nuestro modelo XGBoost analiza más de 25 variables por partido para calcular probabilidades independientes del mercado.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Step cards */}
          {[
            {
              num: '01',
              title: 'Ingesta de datos',
              desc: 'Actualizamos continuamente puntos Elo de clubes, estadísticas xG, historial H2H, forma reciente (últimas 6 jornadas), lesiones relevantes y contexto de jornada.',
              highlight: '25+ variables',
            },
            {
              num: '02',
              title: 'Modelo probabilístico',
              desc: 'Un ensamble de XGBoost + Random Forest calibrado con datos históricos de La Liga desde 2015 genera probabilidades reales para los mercados 1X2 y O/U 2.5.',
              highlight: 'XGBoost + RF ensemble',
            },
            {
              num: '03',
              title: 'Detección de ineficiencias',
              desc: 'Comparamos nuestras probabilidades con las cuotas implícitas de las principales casas. Cuando el edge supera el umbral dinámico, se etiqueta como value bet.',
              highlight: 'Edge > umbral dinámico',
            },
            {
              num: '04',
              title: 'Clasificación de riesgo',
              desc: 'Cada apuesta se clasifica como Bajo, Medio, Alto o Lotería según el edge esperado y la calibración histórica del modelo para ese tipo de partido.',
              highlight: '4 niveles de riesgo',
            },
          ].map(({ num, title, desc, highlight }) => (
            <div key={num} className="p-8 rounded-2xl bg-[#161B22] border border-white/[0.07] flex gap-6">
              <div className="shrink-0">
                <span className="text-4xl font-bold text-white/[0.06]">{num}</span>
              </div>
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#1B365D]/30 border border-[#1B365D]/40 text-[#7BA7C9] text-[10px] font-bold uppercase tracking-widest mb-3">
                  {highlight}
                </div>
                <h3 className="font-bold text-lg text-white mb-2">{title}</h3>
                <p className="text-white/50 text-sm leading-relaxed">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
           RENDIMIENTO / STATS
      ══════════════════════════════════════════════════════════════ */}
      <section id="rendimiento" className="relative z-10 py-28 bg-[#0A0E13] border-y border-white/[0.05]">
        <div className="max-w-6xl mx-auto px-6 lg:px-12">
          <div className="text-center mb-16">
            <p className="text-[#C8A252] text-xs font-bold uppercase tracking-[0.25em] mb-4">Rendimiento</p>
            <h2 className="text-4xl lg:text-5xl font-bold mb-4">Resultados verificables</h2>
            <p className="text-white/50 max-w-xl mx-auto">
              Datos del último trimestre. Simulación a stake fijo de 1u por apuesta calificada.
            </p>
          </div>

          {/* Big numbers */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
            {[
              { value: '85%', label: 'Precisión riesgo bajo', color: 'text-white' },
              { value: '+18%', label: 'ROI promedio', color: 'text-[#C8A252]' },
              { value: '247', label: 'Apuestas analizadas', color: 'text-white' },
              { value: '70%', label: 'Precisión riesgo medio', color: 'text-white' },
            ].map(({ value, label, color }) => (
              <div key={label} className="p-6 rounded-2xl bg-[#161B22] border border-white/[0.07] text-center">
                <div className={`text-4xl lg:text-5xl font-bold mb-2 ${color}`}>{value}</div>
                <div className="text-white/40 text-sm">{label}</div>
              </div>
            ))}
          </div>

          {/* Progress bars */}
          <div className="max-w-2xl mx-auto space-y-5">
            {[
              { label: 'Riesgo bajo', pct: 85, color: 'bg-[#C8A252]', textColor: 'text-[#C8A252]' },
              { label: 'Riesgo medio', pct: 70, color: 'bg-[#7BA7C9]', textColor: 'text-[#7BA7C9]' },
              { label: 'Riesgo alto', pct: 52, color: 'bg-white/30', textColor: 'text-white/50' },
            ].map(({ label, pct, color, textColor }) => (
              <div key={label}>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-white/70 font-medium">{label}</span>
                  <span className={`font-bold ${textColor}`}>{pct}%</span>
                </div>
                <div className="h-2 bg-white/[0.06] rounded-full overflow-hidden">
                  <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
                </div>
              </div>
            ))}
          </div>

          <p className="text-center text-white/25 text-xs mt-10 max-w-xl mx-auto">
            * Los rendimientos históricos no garantizan resultados futuros. Las apuestas deportivas conllevan riesgo de pérdida económica. Solo mayores de 18 años.
          </p>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
           TESTIMONIOS
      ══════════════════════════════════════════════════════════════ */}
      <section className="relative z-10 py-28 px-6 lg:px-12 max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <p className="text-[#C8A252] text-xs font-bold uppercase tracking-[0.25em] mb-4">Testimonios</p>
          <h2 className="text-4xl lg:text-5xl font-bold mb-4">Lo que dicen los usuarios</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            {
              initials: 'JM',
              name: 'Javier M.',
              role: 'Usuario Pro · 3 meses',
              quote: 'Primera herramienta que me da contexto real detrás de cada predicción. El análisis de puntos Elo vs cuotas es lo que me faltaba para dejar de apostar al azar.',
              stars: 5,
            },
            {
              initials: 'SR',
              name: 'Sara R.',
              role: 'Usuario Pro · 2 meses',
              quote: 'El badge de riesgo es lo más útil. Ya no tengo que adivinar si merece la pena entrar a una cuota. La clasificación Bajo / Medio / Alto lo cambia todo.',
              stars: 5,
            },
            {
              initials: 'AL',
              name: 'Adrián L.',
              role: 'Usuario Pro · 5 meses',
              quote: 'Llevo usando varios servicios de tipsters y QuantStake es el único que me muestra la metodología detrás. La transparencia es lo que me convenció.',
              stars: 5,
            },
          ].map(({ initials, name, role, quote, stars }) => (
            <div key={name} className="p-8 rounded-2xl bg-[#161B22] border border-white/[0.07] flex flex-col">
              {/* Stars */}
              <div className="flex gap-1 mb-5">
                {Array.from({ length: stars }).map((_, i) => <StarIcon key={i} />)}
              </div>
              <p className="text-white/70 leading-relaxed text-sm flex-1 mb-6">"{quote}"</p>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-[#1B365D] flex items-center justify-center text-xs font-bold text-[#C8A252]">
                  {initials}
                </div>
                <div>
                  <p className="font-semibold text-sm text-white">{name}</p>
                  <p className="text-white/40 text-xs">{role}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
           PRECIOS
      ══════════════════════════════════════════════════════════════ */}
      <section id="precios" className="relative z-10 py-28 bg-[#0A0E13] border-y border-white/[0.05]">
        <div className="max-w-5xl mx-auto px-6 lg:px-12">
          <div className="text-center mb-16">
            <p className="text-[#C8A252] text-xs font-bold uppercase tracking-[0.25em] mb-4">Precio</p>
            <h2 className="text-4xl lg:text-5xl font-bold mb-4">Simple y sin sorpresas</h2>
            <p className="text-white/50 max-w-xl mx-auto">Sin contratos anuales. Sin permanencia. Cancela cuando quieras.</p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-3xl mx-auto">

            {/* Free plan */}
            <div className="p-8 rounded-3xl bg-[#161B22] border border-white/[0.07]">
              <div className="mb-6">
                <h3 className="text-xl font-bold mb-1">Free</h3>
                <p className="text-white/40 text-sm">Para empezar a explorar</p>
              </div>
              <div className="flex items-baseline gap-1 mb-8">
                <span className="text-4xl font-bold">0€</span>
                <span className="text-white/40">/mes</span>
              </div>
              <ul className="space-y-3 mb-8">
                {[
                  'Acceso al dashboard de partidos',
                  'Vista previa de predicciones',
                  '4 análisis completos al mes',
                  'Sin tarjeta de crédito',
                ].map(f => (
                  <li key={f} className="flex items-start gap-3 text-sm text-white/60">
                    <CheckIcon />
                    {f}
                  </li>
                ))}
              </ul>
              <Link href="/register" className="block w-full py-3.5 rounded-xl border border-white/15 text-white font-bold text-center hover:bg-white/5 transition-colors text-sm">
                Crear cuenta gratis
              </Link>
            </div>

            {/* Pro plan */}
            <div className="relative p-8 rounded-3xl bg-gradient-to-b from-[#1B365D]/40 to-[#0D1117] border border-[#C8A252]/30 shadow-[0_0_60px_rgba(200,162,82,0.1)]">
              <div className="absolute -top-3.5 right-8">
                <span className="px-4 py-1.5 rounded-full bg-[#C8A252] text-[#0D1117] text-xs font-bold uppercase tracking-wider shadow-lg">
                  Más popular
                </span>
              </div>

              <div className="mb-4">
                <h3 className="text-xl font-bold mb-1">Pro</h3>
                <p className="text-white/40 text-sm">Para inversores serios</p>
              </div>

              <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-[#C8A252]/10 border border-[#C8A252]/20 mb-6">
                <span className="w-2 h-2 rounded-full bg-[#C8A252] animate-pulse shrink-0" />
                <div>
                  <p className="text-[#C8A252] text-xs font-black uppercase tracking-widest">7 días GRATIS</p>
                  <p className="text-white/40 text-[11px]">Después, solo 9,99€/mes. Cancela gratis antes.</p>
                </div>
              </div>

              <div className="flex items-baseline gap-1 mb-8">
                <span className="text-4xl font-bold text-white">9,99€</span>
                <span className="text-white/40">/mes</span>
              </div>

              <ul className="space-y-3 mb-8">
                {[
                  'Predicciones ilimitadas en tiempo real',
                  'Análisis IA completo por partido',
                  'Alertas value bet instantáneas',
                  'Mercados 1X2 + Over/Under 2.5',
                  'Gestión de bankroll integrada',
                  'Todos los partidos desbloqueados',
                  'Soporte prioritario',
                ].map(f => (
                  <li key={f} className="flex items-start gap-3 text-sm text-white/80">
                    <CheckIcon />
                    {f}
                  </li>
                ))}
              </ul>

              <Link
                href="/register"
                className="block w-full py-4 rounded-xl bg-[#C8A252] text-[#0D1117] font-bold text-center hover:bg-[#d4b06a] transition-all shadow-[0_0_30px_rgba(200,162,82,0.2)] text-sm"
              >
                Empezar 7 días gratis →
              </Link>
              <p className="text-center text-white/25 text-[10px] mt-3">Sin permanencia · Sin tarjeta hasta que decidas continuar</p>
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
           FAQ
      ══════════════════════════════════════════════════════════════ */}
      <section id="faq" className="relative z-10 py-28 px-6 lg:px-12 max-w-4xl mx-auto">
        <div className="text-center mb-16">
          <p className="text-[#C8A252] text-xs font-bold uppercase tracking-[0.25em] mb-4">FAQ</p>
          <h2 className="text-4xl lg:text-5xl font-bold">Preguntas frecuentes</h2>
        </div>

        <div className="space-y-0 divide-y divide-white/[0.07]">
          {[
            {
              q: '¿Qué es exactamente una "value bet"?',
              a: 'Una value bet ocurre cuando la probabilidad real de un resultado es mayor que la probabilidad implícita en la cuota de la casa. En términos simples: la casa está equivocada y estás pagando más de lo que debería valer esa apuesta. Nuestro modelo calcula esas probabilidades de forma independiente.',
            },
            {
              q: '¿El sistema garantiza ganancias?',
              a: 'No. El análisis estadístico favorece al apostante a largo plazo, pero las apuestas deportivas conllevan riesgo. Ninguna herramienta puede garantizar ganancias. El objetivo es obtener edge estadístico en un volumen suficiente de apuestas, no ganar cada una individualmente.',
            },
            {
              q: '¿Debo apostar a todas las value bets que señala el sistema?',
              a: 'No necesariamente. El sistema clasifica cada predicción por nivel de riesgo (Bajo, Medio, Alto, Lotería). Te recomendamos centrarte en las de riesgo Bajo y gestionar siempre el bankroll con disciplina. Las de riesgo Alto tienen mayor edge potencial pero también mayor volatilidad.',
            },
            {
              q: '¿En qué deportes y competiciones funciona?',
              a: 'Actualmente especializado en fútbol: La Liga española (clubes) y selecciones internacionales (Copa del Mundo, Eurocopa, Nations League). Iremos ampliando la cobertura progresivamente.',
            },
            {
              q: '¿Con qué frecuencia se actualiza el modelo?',
              a: 'El modelo se reentrena automáticamente tras cada jornada con los resultados más recientes. Los datos Elo de equipos se actualizan semanalmente. Las cuotas de mercado se monitorizan en tiempo real.',
            },
            {
              q: '¿Cómo funciona la prueba de 7 días?',
              a: 'Al registrarte obtienes acceso completo durante 7 días sin coste. Al finalizar, si no cancelas, la suscripción se renueva a 9,99€/mes. Puedes cancelar en cualquier momento desde tu perfil, sin penalizaciones ni llamadas telefónicas.',
            },
          ].map(({ q, a }) => (
            <details key={q} className="group py-6 cursor-pointer list-none">
              <summary className="flex justify-between items-start gap-4 text-base font-semibold text-white list-none">
                <span>{q}</span>
                <svg className="w-5 h-5 text-white/40 shrink-0 mt-0.5 group-open:rotate-45 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
                </svg>
              </summary>
              <p className="mt-4 text-white/50 leading-relaxed text-sm pr-8">{a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
           CTA FINAL
      ══════════════════════════════════════════════════════════════ */}
      <section className="relative z-10 py-28 px-6 text-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-[#1B365D]/10 via-[#C8A252]/5 to-transparent pointer-events-none" />
        <div className="relative max-w-3xl mx-auto">
          <p className="text-[#C8A252] text-xs font-bold uppercase tracking-[0.25em] mb-6">Empieza hoy</p>
          <h2 className="text-4xl lg:text-6xl font-bold leading-tight mb-6">
            El mercado no espera.
            <br />
            <span className="text-white/40">¿Lo harás tú?</span>
          </h2>
          <p className="text-white/50 text-lg mb-10 max-w-xl mx-auto">
            Únete a más de 500 inversores que ya utilizan datos cuantitativos para tomar mejores decisiones.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/register"
              className="px-10 py-4 rounded-full bg-[#C8A252] text-[#0D1117] font-bold text-lg hover:bg-[#d4b06a] transition-all shadow-[0_0_50px_rgba(200,162,82,0.3)]"
            >
              Prueba gratis 7 días
            </Link>
            <Link
              href="/login"
              className="px-10 py-4 rounded-full border border-white/15 text-white font-bold text-lg hover:bg-white/5 transition-all"
            >
              Ya tengo cuenta
            </Link>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
           FOOTER
      ══════════════════════════════════════════════════════════════ */}
      <footer className="relative z-10 border-t border-white/[0.06] bg-[#0A0E13] py-16 px-6 lg:px-12">
        <div className="max-w-6xl mx-auto">

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-12 mb-12">
            {/* Brand */}
            <div>
              <Image src="/logo.png" alt="QuantStake" width={160} height={44} className="h-9 w-auto object-contain brightness-0 invert mb-4" />
              <p className="text-white/35 text-sm leading-relaxed max-w-xs">
                Plataforma de análisis cuantitativo para detectar ineficiencias en el mercado de apuestas deportivas.
              </p>
            </div>

            {/* Links */}
            <div className="grid grid-cols-2 gap-8">
              <div>
                <p className="text-white/60 text-xs font-bold uppercase tracking-widest mb-4">Producto</p>
                <ul className="space-y-3 text-sm text-white/35">
                  <li><a href="#como-funciona" className="hover:text-white transition-colors">Cómo funciona</a></li>
                  <li><a href="#rendimiento" className="hover:text-white transition-colors">Rendimiento</a></li>
                  <li><a href="#precios" className="hover:text-white transition-colors">Precios</a></li>
                  <li><Link href="/register" className="hover:text-white transition-colors">Empezar gratis</Link></li>
                </ul>
              </div>
              <div>
                <p className="text-white/60 text-xs font-bold uppercase tracking-widest mb-4">Legal</p>
                <ul className="space-y-3 text-sm text-white/35">
                  <li><a href="/terminos" className="hover:text-white transition-colors">Términos y condiciones</a></li>
                  <li><a href="/privacidad" className="hover:text-white transition-colors">Privacidad</a></li>
                  <li><a href="/cookies" className="hover:text-white transition-colors">Cookies</a></li>
                </ul>
              </div>
            </div>

            {/* Disclaimer */}
            <div>
              <p className="text-white/60 text-xs font-bold uppercase tracking-widest mb-4">Aviso legal</p>
              <p className="text-white/25 text-xs leading-relaxed">
                QuantStake es una herramienta de análisis estadístico. No somos una casa de apuestas ni gestionamos fondos de terceros. Las apuestas deportivas conllevan riesgo económico. Los rendimientos pasados no garantizan resultados futuros. Uso exclusivo para mayores de 18 años. Juega con responsabilidad.
              </p>
              <div className="flex items-center gap-3 mt-4">
                <span className="px-2.5 py-1 rounded bg-white/[0.06] text-white/40 text-[10px] font-bold uppercase tracking-widest">+18</span>
                <span className="px-2.5 py-1 rounded bg-white/[0.06] text-white/40 text-[10px] font-bold uppercase tracking-widest">RGPD</span>
                <span className="px-2.5 py-1 rounded bg-white/[0.06] text-white/40 text-[10px] font-bold uppercase tracking-widest">No somos bookmaker</span>
              </div>
            </div>
          </div>

          <div className="pt-8 border-t border-white/[0.06] flex flex-col sm:flex-row justify-between items-center gap-4 text-white/25 text-xs">
            <span>© 2026 QuantStake. Todos los derechos reservados.</span>
            <span>Hecho con datos · Find Your Edge</span>
          </div>
        </div>
      </footer>

    </div>
  );
}
