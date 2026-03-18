import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    status: 'healthy',
    mode: 'DEMO',
    version: '1.0.0',
    services: { database: 'demo', kafka: 'demo', ai: 'demo' },
  });
}
