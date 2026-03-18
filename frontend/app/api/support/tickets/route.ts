import { NextResponse } from 'next/server';

const DEMO_TICKETS = [
  { ticket_id: 'TKT-DEMO-001', subject: 'Cannot login to dashboard', status: 'resolved', priority: 'high', category: 'technical', channel: 'web_form', customer_name: 'Ahmed Khan', customer_email: 'ahmed@example.com', created_at: new Date(Date.now() - 3600000).toISOString(), mode: 'DEMO' },
  { ticket_id: 'TKT-DEMO-002', subject: 'Billing charge question', status: 'processing', priority: 'medium', category: 'billing', channel: 'email', customer_name: 'Sara Ali', customer_email: 'sara@example.com', created_at: new Date(Date.now() - 7200000).toISOString(), mode: 'DEMO' },
  { ticket_id: 'TKT-DEMO-003', subject: 'Feature request: dark mode', status: 'open', priority: 'low', category: 'feedback', channel: 'whatsapp', customer_name: 'Usman Malik', customer_email: 'usman@example.com', created_at: new Date(Date.now() - 10800000).toISOString(), mode: 'DEMO' },
  { ticket_id: 'TKT-DEMO-004', subject: 'App crashes on mobile', status: 'escalated', priority: 'urgent', category: 'bug_report', channel: 'web_form', customer_name: 'Fatima Sheikh', customer_email: 'fatima@example.com', created_at: new Date(Date.now() - 14400000).toISOString(), mode: 'DEMO' },
  { ticket_id: 'TKT-DEMO-005', subject: 'Export to CSV not working', status: 'resolved', priority: 'medium', category: 'technical', channel: 'email', customer_name: 'Ali Hassan', customer_email: 'ali@example.com', created_at: new Date(Date.now() - 18000000).toISOString(), mode: 'DEMO' },
];

export async function GET() {
  return NextResponse.json({
    tickets: DEMO_TICKETS,
    total: DEMO_TICKETS.length,
    mode: 'DEMO',
  });
}
