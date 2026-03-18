import { NextRequest, NextResponse } from 'next/server';

function genId(prefix: string) {
  return `${prefix}-${Date.now().toString(36).toUpperCase()}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;
}

const AI_RESPONSES: Record<string, string> = {
  billing: "Thank you for reaching out about your billing concern. I've reviewed your account and can see the details you've mentioned. Our billing team will process this within 1-2 business days. Your ticket has been prioritized. Is there anything else I can help you with?",
  technical: "Thank you for reporting this technical issue. I've analyzed the problem and our engineering team has been notified. As a temporary workaround, please try clearing your browser cache and cookies, then log back in. We're working on a permanent fix and you'll receive an update within 4 hours.",
  bug_report: "Thank you for this detailed bug report — it's very helpful! I've logged it with high priority for our QA team. We aim to release a fix in our next patch (within 48 hours). You'll receive an email notification once it's resolved.",
  general: "Thank you for contacting TechCorp support! I've reviewed your message and I'm happy to help. Based on your inquiry, I've created a support ticket with all the details. A specialist will follow up with you shortly. In the meantime, you can check our help center for immediate answers.",
  feedback: "Thank you so much for your feedback! We truly value your input as it helps us improve TaskFlow Pro. I've shared your thoughts with our product team. We'd love to hear more — would you be open to a brief 10-minute call with our product manager next week?",
};

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { name, email, subject, category = 'general', priority = 'medium', message } = body;

    if (!name || !email || !message) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    const ticketId = genId('TKT');
    const conversationId = genId('CONV');

    const aiReply = AI_RESPONSES[category] ?? AI_RESPONSES.general;

    // Simulate AI processing delay
    await new Promise(r => setTimeout(r, 800));

    return NextResponse.json({
      ticket_id: ticketId,
      conversation_id: conversationId,
      status: 'processing',
      channel: 'web_form',
      estimated_response: '< 5 minutes',
      message: `Ticket ${ticketId} created. ${aiReply}`,
      mode: 'DEMO',
      ai_response: aiReply,
      customer_name: name,
      customer_email: email,
      subject: subject || message.slice(0, 60),
      priority,
      category,
    });
  } catch {
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
