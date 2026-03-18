import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    escalations: [
      { ticket_id: 'TKT-DEMO-004', reason: 'App crashes on mobile', priority: 'urgent', customer_name: 'Fatima Sheikh', created_at: new Date(Date.now() - 14400000).toISOString(), channel: 'web_form' },
      { ticket_id: 'TKT-DEMO-ESC2', reason: 'Repeated billing error', priority: 'high', customer_name: 'Bilal Ahmed', created_at: new Date(Date.now() - 28800000).toISOString(), channel: 'email' },
    ],
    total: 2,
    mode: 'DEMO',
  });
}
