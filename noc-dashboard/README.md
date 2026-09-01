# NOC Dashboard — Milan Grid

Lightweight React NOC Dashboard (Phase 5: RE1–RE5) built with Vite, React Router,
Recharts and React-Leaflet. Consumes the FastAPI endpoints built in Phase 4 (API1–API6).

---

## Prerequisites

- Node.js LTS (18 or 20)
- The FastAPI backend running on `http://localhost:8000`

---

## Setup

```bash
# 1. Install dependencies
npm install

# 2. (Optional) copy and adjust the API URL
cp .env.example .env
# Edit VITE_API_BASE_URL if your FastAPI runs on a different port

# 3. Add the Milan grid GeoJSON for the hotspot map
#    Copy milano-grid.geojson into:
mkdir -p public/reference
cp /path/to/milano-grid.geojson public/reference/

# 4. Start the dev server
npm run dev
```

The app will be available at http://localhost:5173

---

## Pages

| Route         | Page               | Consumes         |
|---------------|--------------------|------------------|
| `/`           | Network Overview   | `GET /network/summary`               |
| `/grid`       | Grid Explorer      | `GET /network/grid/{grid_id}`        |
| `/grid/:id`   | Grid Explorer      | same, pre-loaded |
| `/hotspots`   | Hotspots & Alerts  | `GET /network/hotspots`, `/alerts`   |
| `/predict`    | Predictive Risk    | `POST /network/predict-risk`, `GET /network/grid/{id}/features` |
| `/pipeline`   | Pipeline Status    | `GET /pipeline/status`               |

---

## GeoJSON map note

The Milan hotspot map (`/hotspots`) loads `public/reference/milano-grid.geojson`
once on page load and keeps it in memory. Only the grids returned by the API are
rendered as coloured polygons — all 10 000 cells are NOT drawn, which keeps the
page responsive.

**Join key**: `properties.cellId` (1-based), never the top-level `id` (0-based).

---

## Environment variables

| Variable             | Default                   | Description                  |
|----------------------|---------------------------|------------------------------|
| `VITE_API_BASE_URL`  | `http://localhost:8000`   | Base URL of the FastAPI app  |

---

## Build for production

```bash
npm run build
# Outputs to dist/
```
