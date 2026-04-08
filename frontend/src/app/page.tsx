/**
 * page.tsx  — Server Component with ISR
 * ----------------------------------------
 * Fetches data once on the server with Next.js ISR (revalidate: 60 seconds).
 * Vercel caches the resulting HTML at the edge and serves it instantly to
 * every user. The cache is refreshed in the background every 60 s by Vercel's
 * edge network — no user ever sees a loading spinner for the initial content.
 *
 * Interactive elements (filters, bet modal, bankroll) live in MatchesDashboard,
 * a separate client component that receives data as props.
 */

import Navbar from '@/components/Navbar';
import MatchesDashboard from '@/components/MatchesDashboard';

// Server-side environment variable (not exposed to the browser)
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

// Revalidate every 60 seconds — Vercel will serve stale HTML and refresh in
// the background. Increase this value if your scheduler interval is longer.
export const revalidate = 60;

// ── Server-side data fetching ─────────────────────────────────────────────────

async function fetchJSON<T>(url: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(url, {
      next: { revalidate },          // ISR cache tag
      headers: { 'Cache-Control': 'no-store' }, // bypass CDN for the origin fetch
    });
    if (!res.ok) return fallback;
    const data = await res.json();
    return data as T;
  } catch {
    return fallback;
  }
}

// ── Page component (Server) ───────────────────────────────────────────────────

export default async function Home() {
  // All three fetches run in parallel on the server
  const [matches, parlay, boosts] = await Promise.all([
    fetchJSON<object[]>(`${API}/api/matches/jornada`, []),
    fetchJSON<object | null>(`${API}/api/perfect_parlay`, null),
    fetchJSON<object[]>(`${API}/api/super-boosts`, []),
  ]);

  // Normalise jornada response (the API may return {status, data, message} while warming up)
  const initialMatches = Array.isArray(matches)
    ? matches
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    : ((matches as any)?.data ?? []);

  return (
    <div className="min-h-screen bg-[#FCF9F1] text-[#1A1C1E] font-sans selection:bg-[#064E3B]/10 selection:text-[#064E3B] overflow-x-hidden">
      <Navbar />

      <main className="pt-32 pb-24 max-w-7xl mx-auto px-8">
        {/*
          MatchesDashboard receives server-fetched data as initial props,
          so the page renders with full content on the first paint.
          All client-side interactivity (filters, modal, bankroll) lives inside.
        */}
        <MatchesDashboard
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          initialMatches={initialMatches as any}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          initialParlay={parlay as any}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          initialBoosts={boosts as any}
        />
      </main>
    </div>
  );
}
