import { NextRequest, NextResponse } from 'next/server';

const DEMO_REPLIES: Record<string, string> = {
  login: "I can help with login issues! First, please try resetting your password via the 'Forgot Password' link. If that doesn't work, clear your browser cache and try again. Still stuck? I'll escalate to our technical team right away.",
  billing: "I understand billing concerns can be stressful. I've reviewed your account and can confirm the charge is for your monthly subscription. If you believe there's an error, I'll connect you with our billing specialist immediately.",
  bug: "Thank you for reporting this bug! I've logged it with high priority for our engineering team. As a workaround, please try using Chrome or Firefox. We'll have a fix deployed within 48 hours.",
  feature: "Great suggestion! I've forwarded your feature request to our product team. We review all requests monthly and will notify you if it makes it into our roadmap.",
  default: "Thank you for contacting TechCorp support! I'm Claude, your AI Customer Success agent. I've analyzed your message and created a support ticket. A resolution will be provided within 5 minutes. How else can I help you today?",
};

export async function POST(req: NextRequest) {
  try {
    const { message = '', channel = 'web_form' } = await req.json();
    const m = message.toLowerCase();

    let reply = DEMO_REPLIES.default;
    if (/login|password|access|sign.?in/.test(m)) reply = DEMO_REPLIES.login;
    else if (/bill|charge|invoice|payment|refund/.test(m)) reply = DEMO_REPLIES.billing;
    else if (/bug|crash|error|broken|not work/.test(m)) reply = DEMO_REPLIES.bug;
    else if (/feature|suggest|idea|request/.test(m)) reply = DEMO_REPLIES.feature;

    await new Promise(r => setTimeout(r, 600));

    return NextResponse.json({
      response: reply,
      channel,
      tools_used: ['search_kb', 'create_ticket', 'send_response'],
      sentiment_score: 0.72,
      escalated: false,
      ticket_id: `TKT-TEST-${Date.now().toString(36).toUpperCase()}`,
      mode: 'DEMO',
    });
  } catch {
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
