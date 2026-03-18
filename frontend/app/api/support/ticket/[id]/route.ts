import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  _req: NextRequest,
  { params }: { params: { id: string } },
) {
  const ticketId = params.id;
  const now = new Date().toISOString();
  const created = new Date(Date.now() - 2 * 60000).toISOString();

  return NextResponse.json({
    ticket_id: ticketId,
    subject: 'Support Request',
    status: 'resolved',
    priority: 'medium',
    category: 'general',
    channel: 'web_form',
    customer_name: 'Customer',
    customer_email: 'customer@example.com',
    created_at: created,
    updated_at: now,
    mode: 'DEMO',
    messages: [
      {
        id: `msg-${Date.now()}-1`,
        role: 'customer',
        direction: 'inbound',
        content: 'I need help with my account.',
        channel: 'web_form',
        created_at: created,
        delivery_status: 'delivered',
      },
      {
        id: `msg-${Date.now()}-2`,
        role: 'agent',
        direction: 'outbound',
        content:
          "Thank you for reaching out! I've reviewed your account and everything looks good. Your issue has been resolved. Please let us know if you need anything else — we're here 24/7!",
        channel: 'web_form',
        created_at: now,
        delivery_status: 'delivered',
      },
    ],
  });
}
