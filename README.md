# FlowGuard Predictive Logistics Engine

FlowGuard is a full-stack logistics risk intelligence platform. It scores shipment risk, simulates alternate routes, evaluates cascading network impact, captures operational outcomes, and provides AI-generated operational recommendations.

The project consists of:
- A FastAPI backend for scoring, simulation, event processing, and learning
- A Next.js frontend for control tower operations and visualization
- A SQLite database used as the system of record

## Core Capabilities

- Dynamic shipment risk scoring with weighted delay factors
- Route simulation with risk/time/cost deltas
- Ripple impact analysis for downstream shipments
- Driver event ingestion and shipment status updates
- Outcome logging and adaptive weight adjustment
- AI analysis endpoint with structured recommendation and fallback behavior

## Project Structure

```text
.
├── backend/               # FastAPI app and domain logic
│   ├── main.py            # API entrypoint
│   ├── scoring.py         # Risk scoring engine
│   ├── simulation.py      # Route A vs Route B simulation
│   ├── ripple.py          # Cascade impact logic
│   ├── event_impact.py    # Event persistence and ETA adjustments
│   ├── learner.py         # Feedback-based weight adjustment
│   ├── agent.py           # LLM-driven analysis orchestration
│   ├── database.py        # SQLite access layer
│   ├── seed.py            # Seed script from JSON fixtures
│   └── requirements.txt
├── frontend/              # Next.js dashboard (App Router)
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── package.json
│   └── .env.example
├── data/                  # Seed data (shipments, routes, nodes, factors)
└── flowguard.db           # Primary SQLite database
```

## Architecture Overview

1. `GET /shipments` computes current risk levels and dashboard summary details.
2. Driver or AI events trigger network impact logic and shipment state updates.
3. `POST /outcome` records prediction outcomes and adjusts scoring weights.
4. Frontend continuously polls and refreshes operational views.
5. AI analysis (`POST /agent/analyse`) combines risk, simulation, and ripple context to produce recommendations.

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm 9+

## Backend Setup

From project root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Seed the database:

```bash
python seed.py
```

Run the API:

```bash
uvicorn main:app --reload
```

Backend will be available at:
- `http://127.0.0.1:8000`

## Frontend Setup

From project root:

```bash
cd frontend
npm install
cp .env.example .env.local
```

Set environment values in `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Run the frontend:

```bash
npm run dev
```

Frontend will be available at:
- `http://localhost:3000`

## Environment Variables

### Backend (`.env` in project root)

- `GOOGLE_API_KEY` (required for live LLM analysis)
- `GOOGLE_MODEL` (optional, default: `gemini-2.0-flash`)

### Frontend (`frontend/.env.local`)

- `NEXT_PUBLIC_API_BASE_URL` (backend base URL used by client API calls)

## API Reference

### Health
- `GET /`

### Risk and Shipment
- `GET /shipments`
- `GET /shipments/{shipment_id}`

### Route Decision
- `GET /decide/{shipment_id}`

### Event and Ripple
- `POST /event`
- `GET /ripple/{shipment_id}?event_type=...`

### Outcomes and Learning
- `POST /outcome`

### AI Analysis
- `POST /agent/analyse`

Example request:

```json
{
  "shipment_id": "DEL-001",
  "event_description": "roadblock reported on primary highway"
}
```

## Notes on AI Analysis Behavior

- AI analysis reads current risk, simulation, and ripple context.
- Event impact updates shipment status and ETA in the database.
- If external model invocation fails, the backend returns a deterministic fallback recommendation to avoid endpoint failure.

## Troubleshooting

- `POST /agent/analyse` returns 500:
  - Verify `GOOGLE_API_KEY`
  - Set a valid `GOOGLE_MODEL`
  - Restart backend after env changes
- Frontend not reaching backend:
  - Confirm `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local`
  - Restart `npm run dev` after env updates
- Risk levels appear stale:
  - Trigger refresh via UI action or wait for polling interval

## Development Commands

Backend syntax check:

```bash
cd backend
python3 -m py_compile main.py agent.py scoring.py simulation.py
```

Frontend lint:

```bash
cd frontend
npm run lint
```

## License

Internal project. Add a formal license section if distributing outside your organization.
