import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
  const days = Number(req.nextUrl.searchParams.get('days') ?? 7);
  return NextResponse.json({
    channels: [
      { channel: 'web_form', total_tickets: 68, resolved: 54, escalated: 3, avg_sentiment: 0.78 },
      { channel: 'email', total_tickets: 41, resolved: 32, escalated: 3, avg_sentiment: 0.71 },
      { channel: 'whatsapp', total_tickets: 18, resolved: 12, escalated: 1, avg_sentiment: 0.69 },
    ],
    days,
    mode: 'DEMO',
  });
}
