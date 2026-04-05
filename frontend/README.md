# EchoMatrix Frontend

Frontend application for the EchoMatrix investigative narrative dashboard.

This React + Vite app is the user-facing workspace for exploring a Reddit-style JSONL corpus through semantic search, trend analysis, topic clustering, and network investigation.

## Overview

The frontend is built around a dark, investigation-focused interface rather than a generic admin panel. It includes:

- a landing page with Aurora visuals and product framing
- a live dashboard overview powered by backend aggregates
- semantic search for ranked retrieval
- time-series views for narrative momentum
- topic clustering and embedding export views
- network graph exploration
- shared UI, layout, and visualization primitives

## Stack

| Layer | Tools |
| --- | --- |
| App framework | React 19 |
| Build tool | Vite 8 |
| Routing | React Router 7 |
| HTTP client | Axios |
| Charts | Recharts |
| Network graph | react-force-graph-2d |
| Visual effects | OGL |
| Icons | lucide-react |

## Requirements

- Node.js 18 or newer
- npm 9 or newer
- EchoMatrix backend running locally or on a reachable deployment

## Quick Start

Install dependencies:

```bash
npm install
```

Create a local environment file:

```bash
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

Set the backend API URL in `.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

Start the dev server:

```bash
npm run dev
```

Default local URL:

```text
http://localhost:5173
```

## Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Start the Vite dev server |
| `npm run build` | Build the production bundle |
| `npm run preview` | Preview the production build locally |
| `npm run lint` | Run ESLint |

## Environment

Required:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

Example deployed value:

```env
VITE_API_BASE_URL=https://your-backend-service.onrender.com/api
```

Important:

- point this to the backend `/api` root
- restart the dev server after changing `.env`

## App Structure

```text
frontend/
├── src/
│   ├── assets/
│   ├── components/
│   │   ├── layout/
│   │   ├── search/
│   │   ├── ui/
│   │   └── visuals/
│   ├── pages/
│   ├── services/
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
├── .env.example
├── package.json
└── README.md
```

## Routes

| Route | Purpose |
| --- | --- |
| `/` | Landing page |
| `/dashboard` | Overview dashboard |
| `/search` | Semantic search |
| `/trends` | Time-series analysis |
| `/timeseries` | Alias for trends |
| `/topics` | Topic clustering |
| `/network` | Network analysis |
| `/about` | Product overview |

## Backend Integration

The frontend talks to the FastAPI backend through:

- [src/services/api.js](./src/services/api.js)

Main endpoints used:

- `GET /api/dashboard/overview`
- `GET /api/stats`
- `GET /api/search`
- `GET /api/timeseries`
- `GET /api/events`
- `GET /api/topics`
- `GET /api/topics/projector`
- `GET /api/network`

## Production Notes

- Route-level code splitting is enabled with `React.lazy`
- dashboard rendering depends on cached backend aggregates for fast first paint
- chart-heavy and graph-heavy screens benefit from backend compression
- `VITE_API_BASE_URL` allows the same build logic to work locally and in deployment

## Development Notes

- Global styling lives in [src/index.css](./src/index.css)
- Layout components live in `src/components/layout`
- Reusable UI primitives live in `src/components/ui`
- Visual effects and decorative components live in `src/components/visuals`
- Page-level screens live in `src/pages`

## Verification

Recommended local check:

```bash
npm run lint
npm run build
```

If the build succeeds, the frontend is production-bundle ready.

## Troubleshooting

### Dashboard is blank or data is missing

Check:

- the backend is running
- `VITE_API_BASE_URL` is correct
- the backend allows the frontend origin

Backend health check:

```text
http://localhost:8000/health
```

### Search, trends, topics, or network page fails to load

This usually means the backend endpoint is unavailable or returning an error.

### `.env` changes are ignored

Restart the Vite dev server after editing environment variables.
