import { NextResponse } from 'next/server';

export async function POST() {
  return NextResponse.json({
    status: 'ok',
    message: 'Demo data loaded successfully (in-memory DEMO mode).',
  });
}
