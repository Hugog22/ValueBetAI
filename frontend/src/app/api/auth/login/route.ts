import { NextResponse } from 'next/server';

export async function POST(request: Request) {
    try {
        const body = await request.json();
        
        // Forward to FastAPI
        const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
        
        const formParams = new URLSearchParams();
        formParams.append('username', body.username);
        formParams.append('password', body.password);
        
        const res = await fetch(`${backendUrl}/api/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formParams,
        });

        const data = await res.json();

        if (!res.ok) {
            return NextResponse.json(data, { status: res.status });
        }

        // Set HttpOnly Cookie
        const response = NextResponse.json({ success: true });
        
        response.cookies.set({
            name: 'auth_token',
            value: data.access_token,
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'lax',
            path: '/',
            maxAge: 30 * 24 * 60 * 60, // 30 days
        });

        return response;
    } catch (error) {
        return NextResponse.json({ detail: 'Error connecting to auth server' }, { status: 500 });
    }
}
