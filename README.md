# TechCorp Customer Success Digital FTE

AI-powered 24/7 customer support system for TaskFlow Pro.
Built with: **Next.js 14 · FastAPI · Claude AI · PostgreSQL · Kafka · Docker · Kubernetes**

---

## Quick Start — DEMO Mode (no API keys except Anthropic)

```bash
# 1. Clone and setup
cd techcorp-fte
cp .env.example .env

# 2. Add your Anthropic API key (the ONLY required key in demo mode)
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" >> .env

# 3. Start with Docker Compose (DEMO mode)
docker-compose -f docker-compose.demo.yml up --build

# 4. Open in browser
open http://localhost:3000          # Frontend
open http://localhost:8000/docs     # API docs
open http://localhost:3000/dashboard  # Admin dashboard
```

## Quick Start — Local Development

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Copy and configure .env
cp ../.env.example ../.env
# Edit .env — set ANTHROPIC_API_KEY at minimum

# Start backend
cd ..
uvicorn backend.api.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
# Opens at http://localhost:3000
```

## Full LIVE Mode (with all integrations)

```bash
cp .env.example .env
# Fill in ALL values in .env:
# - ANTHROPIC_API_KEY
# - DATABASE_URL
# - KAFKA_BOOTSTRAP_SERVERS
# - GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN
# - TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER
# - Set DRY_RUN=false

docker-compose up --build
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Customer Channels                             │
│   Email (Gmail)  │  WhatsApp (Twilio)  │  Web Form (Next.js)   │
└────────┬─────────┴─────────┬───────────┴──────────┬────────────┘
         │                   │                        │
         ▼                   ▼                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (:8000)                        │
│   /webhooks/gmail  │  /webhooks/whatsapp  │  /support/submit    │
└─────────────────────────┬───────────────────────────────────────┘
                           │ Kafka Events
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Kafka Message Bus                               │
│  fte.tickets.incoming │ fte.channels.* │ fte.escalations        │
└─────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Message Processor Worker                        │
│  1. Resolve Customer   2. Get/Create Conversation               │
│  3. Load History       4. Run AI Agent                          │
│  5. Store Response     6. Publish Metrics                       │
└─────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Claude AI Agent (claude-sonnet-4-20250514)         │
│  Tools: search_kb │ create_ticket │ get_history                 │
│         escalate  │ send_response │ analyze_sentiment           │
└─────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PostgreSQL 16 + pgvector                       │
│  customers │ conversations │ messages │ tickets │ knowledge_base │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | System health + mode |
| POST | `/support/submit` | Submit web form |
| GET | `/support/ticket/{id}` | Ticket status + messages |
| GET | `/support/tickets` | List all tickets |
| POST | `/webhooks/gmail` | Gmail Pub/Sub hook |
| POST | `/webhooks/whatsapp` | Twilio WhatsApp hook |
| GET | `/metrics/channels` | Per-channel stats |
| GET | `/metrics/daily` | Today's summary |
| GET | `/metrics/sentiment` | Sentiment trends |
| POST | `/admin/mode` | Switch DEMO/LIVE |
| POST | `/admin/seed` | Seed demo data |
| GET | `/admin/escalations` | Pending escalations |
| POST | `/agent/test` | Test AI agent directly |

Full API docs: `http://localhost:8000/docs`

---

## Environment Modes

| Setting | DEMO (DRY_RUN=true) | LIVE (DRY_RUN=false) |
|---------|---------------------|----------------------|
| Emails | Logged to console | Sent via Gmail API |
| WhatsApp | Logged to console | Sent via Twilio |
| Tickets | UUID generated | Stored in PostgreSQL |
| Kafka | asyncio.Queue | Real Kafka broker |
| Required keys | ANTHROPIC_API_KEY only | All keys required |

---

## Project Structure

```
techcorp-fte/
├── backend/
│   ├── api/main.py              # FastAPI + all endpoints
│   ├── agent/
│   │   ├── customer_success_agent.py  # Main AI agent
│   │   ├── tools.py             # 6 agent tools
│   │   └── prompts.py           # System prompts
│   ├── channels/
│   │   ├── gmail_handler.py     # Gmail integration
│   │   └── whatsapp_handler.py  # Twilio WhatsApp
│   ├── workers/
│   │   └── message_processor.py # Kafka consumer
│   ├── database/
│   │   ├── schema.sql           # PostgreSQL schema
│   │   └── queries.py           # All DB operations
│   ├── kafka_client.py          # Kafka + in-memory fallback
│   └── config.py                # Central configuration
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Landing page
│   │   ├── support/page.tsx     # Support form
│   │   ├── dashboard/page.tsx   # Admin dashboard
│   │   └── ticket/[id]/page.tsx # Ticket status
│   └── components/
│       ├── SupportForm.tsx
│       ├── ModeToggle.tsx
│       ├── ChannelBadge.tsx
│       └── TicketStatus.tsx
├── context/                     # AI knowledge base
├── k8s/                         # Kubernetes manifests
├── docker-compose.yml           # LIVE mode
├── docker-compose.demo.yml      # DEMO mode
└── .env.example
```

---

## Kubernetes Deployment

```bash
# Apply all manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml  # Update with real base64 values first
kubectl apply -f k8s/deployment-api.yaml
kubectl apply -f k8s/deployment-worker.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml

# Check status
kubectl get pods -n customer-success-fte
```

Scales 3–20 pods automatically at 70% CPU utilization.
