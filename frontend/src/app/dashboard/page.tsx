/**
 * page.tsx  — Server Component with ISR
 * ----------------------------------------
 * Fetches initial data on the server with Next.js ISR (revalidate: 60 s).
 * Fetches: LaLiga matches + all CombinAIas.
 *
 * Interactive elements (sport selector, filters, bet modal) live in
 * MatchesDashboard, a separate client component that receives data as props.
 */

import Navbar from '@/components/Navbar';
import MatchesDashboard from '@/components/MatchesDashboard';
import { cookies } from 'next/headers';

const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
const API = `${backendUrl}/api`;

export const dynamic = 'force-dynamic';

async function fetchJSON<T>(url: string, fallback: T, token?: string): Promise<T> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000); // 5s timeout
    
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(url, {
      cache: 'no-store',
      headers,
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    if (!res.ok) return fallback;
    const data = await res.json();
    return data as T;
  } catch {
    return fallback;
  }
}


export default async function Home() {
  const cookieStore = await cookies();
  const token = cookieStore.get('auth_token')?.value;

  // Fetch LaLiga + all CombinAIas in parallel
  const [matches, allParlays] = await Promise.all([
    fetchJSON<object[]>(`${API}/matches/jornada`, [], token),
    fetchJSON<object[]>(`${API}/sports/all_parlays`, [], token),
  ]);

  const initialMatches = Array.isArray(matches)
    ? matches
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    : ((matches as any)?.data ?? []);

  // Prefer LaLiga parlay (now primary), fallback to any other sport
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const initialParlay = (allParlays as any[]).find(p => p.sport === 'laliga') ?? (allParlays as any[])[0] ?? null;

  return (
    <div className="min-h-screen bg-[#FCF9F1] text-[#1A1C1E] font-sans selection:bg-[#064E3B]/10 selection:text-[#064E3B] overflow-x-hidden">
      <Navbar />
      <main className="pt-32 pb-24 max-w-7xl mx-auto px-8">
        <MatchesDashboard 
          initialMatches={initialMatches} 
          initialParlay={initialParlay}
        />
      </main>
    </div>
  );
}
