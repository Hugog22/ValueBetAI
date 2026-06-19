import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
    const token = request.cookies.get('auth_token')?.value;
    const { pathname, search } = request.nextUrl;

    // 1. Protect Frontend Routes (CRIT-10)
    if (pathname.startsWith('/dashboard') || pathname.startsWith('/bankroll')) {
        if (!token) {
            return NextResponse.redirect(new URL('/login', request.url));
        }
    }

    // 2. Proxy API Requests to Backend (CRIT-8)
    // Intercept all /api/ calls EXCEPT /api/auth/ (which are Next.js Route Handlers)
    // Wait, we DO want to proxy /api/auth/me, /api/auth/register, /api/auth/forgot-password, /api/auth/reset-password
    // The only purely Next.js route handlers will be /api/next-auth/login and /api/next-auth/logout to avoid conflicts.
    
    // Let's use /api/proxy/ for all backend calls to be safe and explicit.
    if (pathname.startsWith('/api/proxy/')) {
        const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
        // Remove /api/proxy and replace with /api
        const backendPath = pathname.replace('/api/proxy', '/api');
        const targetUrl = new URL(backendPath + search, backendUrl);
        
        const requestHeaders = new Headers(request.headers);
        // Forward the token from the HttpOnly cookie to the FastAPI backend
        if (token) {
            requestHeaders.set('Authorization', `Bearer ${token}`);
        }
        
        return NextResponse.rewrite(targetUrl, {
            request: {
                headers: requestHeaders,
            },
        });
    }

    return NextResponse.next();
}

export const config = {
    matcher: ['/dashboard/:path*', '/bankroll/:path*', '/api/proxy/:path*'],
};
