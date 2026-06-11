'use client';

interface WorldCupBannerProps {
  matchCount?: number;
}

export default function WorldCupBanner({ matchCount = 0 }: WorldCupBannerProps) {
  return (
    <div className="wc-banner relative overflow-hidden rounded-[2rem] mb-10 p-8 md:p-10">
      {/* Animated shimmer layer */}
      <div className="wc-shimmer-bar" />

      {/* Trophy glow blob */}
      <div className="absolute -right-20 -top-20 w-72 h-72 rounded-full bg-white/5 blur-3xl pointer-events-none" />
      <div className="absolute -left-10 -bottom-10 w-56 h-56 rounded-full bg-amber-400/10 blur-3xl pointer-events-none" />

      <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center gap-6">
        {/* Trophy icon */}
        <div className="wc-trophy-badge flex-shrink-0">
          <span className="text-5xl md:text-6xl" role="img" aria-label="World Cup Trophy">🏆</span>
        </div>

        {/* Text content */}
        <div className="flex-1">
          <p className="text-amber-300 text-[10px] font-black uppercase tracking-[0.25em] mb-2">
            Modo Activo
          </p>
          <h2 className="text-white text-3xl md:text-4xl font-bold tracking-tight leading-tight mb-2">
            FIFA World Cup <span className="text-amber-300">2026™</span>
          </h2>
          <p className="text-white/70 text-sm font-medium max-w-xl">
            La IA analiza rankings FIFA, calidad de plantilla y estadísticas individuales de jugadores
            para ofrecerte las mejores predicciones del Mundial.
          </p>
        </div>

        {/* Stats pill */}
        <div className="flex flex-col items-center justify-center bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl px-6 py-4 text-center flex-shrink-0">
          <span className="text-3xl font-black text-amber-300">{matchCount}</span>
          <span className="text-white/60 text-[10px] font-bold uppercase tracking-widest mt-0.5">
            {matchCount === 1 ? 'Partido' : 'Partidos'}<br />Disponibles
          </span>
        </div>
      </div>

      {/* Host countries strip */}
      <div className="relative z-10 mt-6 flex items-center gap-3 text-white/50 text-xs font-bold uppercase tracking-widest">
        <span className="text-base">🇺🇸</span>
        <span>Estados Unidos</span>
        <span className="text-white/30">·</span>
        <span className="text-base">🇨🇦</span>
        <span>Canadá</span>
        <span className="text-white/30">·</span>
        <span className="text-base">🇲🇽</span>
        <span>México</span>
      </div>
    </div>
  );
}
