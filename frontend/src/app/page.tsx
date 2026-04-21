/**
 * page.tsx  — Server Component with ISR
 * ----------------------------------------
 * Fetches initial data on the server with Next.js ISR (revalidate: 60 s).
 * Fetches: LaLiga jornada + all CombinAIas across all sports.
 *
 * Interactive elements (sport selector, filters, bet modal) live in
 * MatchesDashboard, a separate client component that receives data as props.
 */

import Navbar from '@/components/Navbar';
import MatchesDashboard from '@/components/MatchesDashboard';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export const revalidate = 60;

async function fetchJSON<T>(url: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(url, {
      next: { revalidate },
      headers: { 'Cache-Control': 'no-store' },
    });
    if (!res.ok) return fallback;
    const data = await res.json();
    return data as T;
  } catch {
    return fallback;
  }
}

export default async function Home() {
  // Fetch LaLiga matches + all CombinAIas in parallel
  const [matches, allParlays] = await Promise.all([
    fetchJSON<object[]>(`${API}/api/matches/jornada`, []),
    fetchJSON<object[]>(`${API}/api/sports/all_parlays`, []),
  ]);

  const initialMatches = Array.isArray(matches)
    ? matches
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    : ((matches as any)?.data ?? []);

  // Use the first parlay (LaLiga) as the initialParlay for backward compat
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const initialParlay = (allParlays as any[])[0] ?? null;

  return (
    <div className="min-h-screen bg-[#FCF9F1] text-[#1A1C1E] font-sans selection:bg-[#064E3B]/10 selection:text-[#064E3B] overflow-x-hidden">
      <Navbar />
      <main className="pt-32 pb-24 max-w-7xl mx-auto px-8">
        <MatchesDashboard
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          initialMatches={initialMatches as any}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          initialParlay={initialParlay as any}
        />
      </main>
    </div>
  );
}
