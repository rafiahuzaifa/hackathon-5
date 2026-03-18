import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
  const days = Number(req.nextUrl.searchParams.get('days') ?? 7);
  const data = Array.from({ length: days }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (days - 1 - i));
    return {
      date: d.toISOString().slice(0, 10),
      avg_sentiment: +(0.65 + Math.random() * 0.25).toFixed(2),
      ticket_count: Math.floor(15 + Math.random() * 20),
    };
  });
  return NextResponse.json({ data, days, mode: 'DEMO' });
}
