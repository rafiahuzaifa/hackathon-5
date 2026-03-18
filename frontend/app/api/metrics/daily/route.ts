import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    total_tickets: 127,
    resolved_tickets: 98,
    escalated_tickets: 7,
    avg_resolution_minutes: 4.2,
    avg_sentiment_score: 0.74,
    ai_handled_pct: 87.5,
    mode: 'DEMO',
    period: 'today',
  });
}
