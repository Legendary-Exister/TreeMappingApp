-- ==============================================================================
-- tree_links table
--
-- When an OSM tree lies within 3 m of a city_register tree the importer
-- records the link here instead of inserting a duplicate tree row.
-- Each (osm_source_id, register_source_id) pair is unique so repeated runs
-- are fully idempotent.
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.tree_links (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    -- source_id of the OSM tree (matches trees.source_id where source='osm')
    osm_source_id       TEXT        NOT NULL,
    -- source_id of the city-register tree (matches trees.source_id where source='city_register')
    register_source_id  TEXT        NOT NULL,
    -- Great-circle distance in metres between the two points at link time
    distance_m          NUMERIC(8, 3) NOT NULL CHECK (distance_m >= 0),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Unique constraint that makes upserts idempotent
CREATE UNIQUE INDEX IF NOT EXISTS idx_tree_links_unique
    ON public.tree_links (osm_source_id, register_source_id);

-- Fast look-up by either side of the link
CREATE INDEX IF NOT EXISTS idx_tree_links_osm_source_id
    ON public.tree_links (osm_source_id);

CREATE INDEX IF NOT EXISTS idx_tree_links_register_source_id
    ON public.tree_links (register_source_id);

-- ==============================================================================
-- Row Level Security
-- ==============================================================================

ALTER TABLE public.tree_links ENABLE ROW LEVEL SECURITY;

-- Everyone can read links (same as trees)
CREATE POLICY "Tree links are readable by everyone"
    ON public.tree_links FOR SELECT
    USING (true);

-- Only the service role (import pipeline) writes links
CREATE POLICY "Service role can manage tree links"
    ON public.tree_links FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ==============================================================================
-- Grants (mirror the pattern from the trees schema migration)
-- ==============================================================================

GRANT SELECT ON public.tree_links TO anon, authenticated;
GRANT ALL    ON public.tree_links TO service_role;
