import { NextResponse } from 'next/server';

export async function POST() {
  return NextResponse.json({
    current_mode: 'DEMO',
    message: 'Running in DEMO mode. Set DRY_RUN=false and configure all env vars to switch to LIVE.',
  });
}
