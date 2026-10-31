# TreeMap Monorepo

A citizen-science web and mobile platform to map and monitor urban city trees. Seeded from open municipal tree registers and OpenStreetMap, updated by citizens with measurements and photos, and verified by reviewers.

## Stack Overview

- **Monorepo Manager:** [pnpm](https://pnpm.io/) (v12) workspaces + [Turborepo](https://turbo.build/) (v2)
- **Web App (`apps/web`):** Next.js 15 (App Router), TypeScript, Tailwind CSS, MapLibre GL JS
- **Mobile App (`apps/mobile`):** Expo (React Native), TypeScript, MapLibre Native (`@maplibre/maplibre-react-native`)
- **Shared Packages (`packages/*`):**
  - `packages/types`: Strict TypeScript schemas & Zod validation
  - `packages/api-client`: Unified typed client for Supabase & tree APIs
- **Data Ingest (`services/ingest`):** Python 3.12 data pipelines with Astral `uv`, GeoPandas, Shapely & Overpass API
- **Backend & Database (`supabase/`):** Supabase (PostgreSQL 15+ with PostGIS extension), Row Level Security (RLS), Edge Functions

> **Map Engine:** Exclusively [MapLibre GL](https://maplibre.org/) with open vector tiles (OpenFreeMap / PMTiles). **No Google Maps, No Mapbox.**

---

## Prerequisites

- **Node.js:** `>= 20.x` (detected: `v24.19.0`)
- **pnpm:** `>= 9.x` (installed: `v12.15.0`)
- **Python:** `>= 3.12` (managed via `uv`)
- **Supabase CLI:** `>= 2.x` (installed: `v2.122.0`)
- **Docker:** (running for local Supabase)

---

## Quick Start

### 1. Install Dependencies

```bash
# Install JS/TS dependencies across all workspaces
pnpm install

# Setup Python 3.12 ingest virtual environment
pnpm run ingest:setup
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

### 3. Start Supabase (Postgres + PostGIS)

```bash
pnpm run supabase:start
```

This launches local Postgres with PostGIS, Auth, and Storage, applying migrations in `supabase/migrations/`.

### 4. Run Development Servers

```bash
# Run web app and packages in dev mode
pnpm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the MapLibre GL map.

To launch the mobile app:

```bash
cd apps/mobile && pnpm run start
```

---

## Monorepo Commands

- `pnpm run dev` - Launch web development server
- `pnpm run build` - Build all packages and applications with Turborepo
- `pnpm run lint` - Lint codebase
- `pnpm run typecheck` - Run TypeScript typecheck across all workspaces
- `pnpm run test` - Run Vitest test suites
- `pnpm run ingest:test` - Run pytest on Python 3.12 ingest pipelines
- `pnpm run format` - Format code with Prettier

---

## Project Structure

```
├── apps/
│   ├── web/                    # Next.js (App Router) + MapLibre GL web application
│   └── mobile/                 # Expo (React Native) + MapLibre Native mobile app
├── packages/
│   ├── types/                  # Zod schemas and TypeScript domain types
│   └── api-client/             # Supabase & TreeMap shared API client
├── services/
│   └── ingest/                 # Python 3.12 pipelines (OSM & city registers)
├── supabase/
│   ├── migrations/             # SQL migrations (PostGIS, RLS, functions)
│   └── functions/              # Edge functions (e.g. identify-tree)
├── docs/
│   └── decisions.md            # Architecture Decision Records (ADRs)
└── turbo.json                  # Turborepo task pipeline configuration
```
