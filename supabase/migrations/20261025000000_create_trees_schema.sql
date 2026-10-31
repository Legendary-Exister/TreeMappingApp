-- ==============================================================================
-- TreeMap Supabase PostGIS Migration
-- ==============================================================================

-- 1. Enable PostGIS in extensions schema
CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA extensions;

-- 2. Custom Enumerated Types
DO $$ BEGIN
    CREATE TYPE public.tree_source AS ENUM ('city_register', 'osm', 'citizen');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE public.tree_status AS ENUM ('unverified', 'verified', 'disputed', 'removed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE public.leaf_cycle AS ENUM ('deciduous', 'evergreen', 'semi_evergreen', 'unknown');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE public.tree_health AS ENUM ('good', 'fair', 'poor', 'dead');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE public.user_role AS ENUM ('citizen', 'reviewer', 'admin');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE public.photo_tag AS ENUM ('whole', 'bark', 'leaf', 'crown');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE public.care_event_type AS ENUM ('watered', 'mulched', 'pruned', 'reported_damage');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE public.verification_verdict AS ENUM ('approved', 'rejected', 'correction_needed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 3. Profiles table (linked to auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username TEXT UNIQUE,
    role public.user_role NOT NULL DEFAULT 'citizen',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Trees table
CREATE TABLE IF NOT EXISTS public.trees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    geom extensions.geography(Point, 4326) NOT NULL,
    source public.tree_source NOT NULL,
    source_id TEXT NOT NULL,
    licence TEXT NOT NULL,
    status public.tree_status NOT NULL DEFAULT 'unverified',
    genus TEXT,
    species TEXT,
    leaf_cycle public.leaf_cycle,
    circumference_m NUMERIC(5,2),
    height_m NUMERIC(5,2),
    crown_diameter_m NUMERIC(5,2),
    planted_year INT,
    raw_attributes JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for trees
CREATE INDEX IF NOT EXISTS idx_trees_geom ON public.trees USING GIST (geom);
CREATE UNIQUE INDEX IF NOT EXISTS idx_trees_source_unique ON public.trees (source, source_id);
CREATE INDEX IF NOT EXISTS idx_trees_species ON public.trees (genus, species);
CREATE INDEX IF NOT EXISTS idx_trees_status ON public.trees (status);

-- 5. Observations table
CREATE TABLE IF NOT EXISTS public.observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES public.trees(id) ON DELETE CASCADE,
    health public.tree_health NOT NULL,
    surroundings TEXT,
    notes TEXT,
    author UUID REFERENCES auth.users(id) ON DELETE SET NULL DEFAULT auth.uid(),
    author_id UUID REFERENCES auth.users(id) ON DELETE SET NULL DEFAULT auth.uid(),
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_observations_tree_id ON public.observations(tree_id);
CREATE INDEX IF NOT EXISTS idx_observations_author ON public.observations(author);
CREATE INDEX IF NOT EXISTS idx_observations_author_id ON public.observations(author_id);

-- Trigger to sync author and author_id on observations
CREATE OR REPLACE FUNCTION public.sync_observation_author()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    NEW.author := COALESCE(NEW.author, NEW.author_id, auth.uid());
    NEW.author_id := NEW.author;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sync_observation_author ON public.observations;
CREATE TRIGGER trg_sync_observation_author
BEFORE INSERT OR UPDATE ON public.observations
FOR EACH ROW
EXECUTE FUNCTION public.sync_observation_author();

-- 6. Photos table
CREATE TABLE IF NOT EXISTS public.photos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES public.trees(id) ON DELETE CASCADE,
    observation_id UUID REFERENCES public.observations(id) ON DELETE CASCADE,
    photo_url TEXT NOT NULL,
    tag public.photo_tag NOT NULL DEFAULT 'whole',
    author UUID REFERENCES auth.users(id) ON DELETE SET NULL DEFAULT auth.uid(),
    author_id UUID REFERENCES auth.users(id) ON DELETE SET NULL DEFAULT auth.uid(),
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_photos_tree_id ON public.photos(tree_id);
CREATE INDEX IF NOT EXISTS idx_photos_author ON public.photos(author);
CREATE INDEX IF NOT EXISTS idx_photos_author_id ON public.photos(author_id);
CREATE INDEX IF NOT EXISTS idx_photos_verified ON public.photos(verified);

-- Trigger to sync author and author_id on photos
CREATE OR REPLACE FUNCTION public.sync_photo_author()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    NEW.author := COALESCE(NEW.author, NEW.author_id, auth.uid());
    NEW.author_id := NEW.author;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sync_photo_author ON public.photos;
CREATE TRIGGER trg_sync_photo_author
BEFORE INSERT OR UPDATE ON public.photos
FOR EACH ROW
EXECUTE FUNCTION public.sync_photo_author();

-- 7. Verifications table
CREATE TABLE IF NOT EXISTS public.verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES public.trees(id) ON DELETE CASCADE,
    reviewer_id UUID REFERENCES auth.users(id) ON DELETE SET NULL DEFAULT auth.uid(),
    verdict public.verification_verdict NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_verifications_tree_id ON public.verifications(tree_id);
CREATE INDEX IF NOT EXISTS idx_verifications_reviewer ON public.verifications(reviewer_id);

-- 8. Care events table (watering, mulching, etc.)
CREATE TABLE IF NOT EXISTS public.care_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tree_id UUID NOT NULL REFERENCES public.trees(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL DEFAULT auth.uid(),
    event_type public.care_event_type NOT NULL,
    litres NUMERIC(6,2),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_care_events_tree_id ON public.care_events(tree_id);
CREATE INDEX IF NOT EXISTS idx_care_events_user_id ON public.care_events(user_id);

-- ==============================================================================
-- Spatial & Helper Functions
-- ==============================================================================

-- Helper function to check if current user is a reviewer or admin
CREATE OR REPLACE FUNCTION public.is_reviewer()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND role IN ('reviewer', 'admin')
    );
$$;

-- Spatial query function to find trees within radius_m of (lon, lat)
CREATE OR REPLACE FUNCTION public.trees_near(
    lon DOUBLE PRECISION,
    lat DOUBLE PRECISION,
    radius_m DOUBLE PRECISION DEFAULT 50.0
)
RETURNS TABLE (
    id UUID,
    source public.tree_source,
    source_id TEXT,
    licence TEXT,
    status public.tree_status,
    genus TEXT,
    species TEXT,
    leaf_cycle public.leaf_cycle,
    circumference_m NUMERIC,
    height_m NUMERIC,
    crown_diameter_m NUMERIC,
    planted_year INT,
    longitude DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    distance_m DOUBLE PRECISION
)
LANGUAGE sql
STABLE
SECURITY INVOKER
PARALLEL SAFE
AS $$
    SELECT
        t.id,
        t.source,
        t.source_id,
        t.licence,
        t.status,
        t.genus,
        t.species,
        t.leaf_cycle,
        t.circumference_m,
        t.height_m,
        t.crown_diameter_m,
        t.planted_year,
        extensions.ST_X(t.geom::extensions.geometry) AS longitude,
        extensions.ST_Y(t.geom::extensions.geometry) AS latitude,
        extensions.ST_Distance(
            t.geom,
            extensions.ST_SetSRID(extensions.ST_MakePoint(lon, lat), 4326)::extensions.geography
        ) AS distance_m
    FROM public.trees t
    WHERE extensions.ST_DWithin(
        t.geom,
        extensions.ST_SetSRID(extensions.ST_MakePoint(lon, lat), 4326)::extensions.geography,
        radius_m
    )
    ORDER BY distance_m ASC;
$$;

-- Atomic submission function for citizen contributions
CREATE OR REPLACE FUNCTION public.submit_tree_with_observation(
    tree_data JSONB,
    observation_data JSONB,
    photo_urls TEXT[]
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
    new_tree_id UUID;
    new_obs_id UUID;
    photo_url TEXT;
    lat DOUBLE PRECISION;
    lon DOUBLE PRECISION;
BEGIN
    IF auth.uid() IS NULL THEN
        RAISE EXCEPTION 'Authentication is required to submit a tree'
            USING ERRCODE = '42501';
    END IF;

    lat := (tree_data->>'latitude')::DOUBLE PRECISION;
    lon := (tree_data->>'longitude')::DOUBLE PRECISION;

    IF lat NOT BETWEEN -90 AND 90 OR lon NOT BETWEEN -180 AND 180 THEN
        RAISE EXCEPTION 'Tree coordinates are outside valid latitude/longitude ranges'
            USING ERRCODE = '22023';
    END IF;

    -- Insert tree as citizen source
    INSERT INTO public.trees (
        geom,
        source,
        source_id,
        licence,
        status,
        genus,
        species,
        circumference_m,
        height_m,
        crown_diameter_m
    ) VALUES (
        extensions.ST_SetSRID(extensions.ST_MakePoint(lon, lat), 4326)::extensions.geography,
        'citizen',
        gen_random_uuid()::text,
        'CC-BY-4.0',
        'unverified',
        tree_data->>'genus',
        tree_data->>'species',
        (tree_data->>'circumference_m')::NUMERIC,
        (tree_data->>'height_m')::NUMERIC,
        (tree_data->>'crown_diameter_m')::NUMERIC
    )
    RETURNING id INTO new_tree_id;

    -- Insert observation
    INSERT INTO public.observations (
        tree_id,
        health,
        surroundings,
        notes,
        author,
        author_id
    ) VALUES (
        new_tree_id,
        (observation_data->>'health')::public.tree_health,
        observation_data->>'surroundings',
        observation_data->>'notes',
        auth.uid(),
        auth.uid()
    )
    RETURNING id INTO new_obs_id;

    -- Insert photos
    IF photo_urls IS NOT NULL THEN
        FOREACH photo_url IN ARRAY photo_urls
        LOOP
            INSERT INTO public.photos (
                tree_id,
                observation_id,
                photo_url,
                author,
                author_id,
                verified
            ) VALUES (
                new_tree_id,
                new_obs_id,
                photo_url,
                auth.uid(),
                auth.uid(),
                FALSE
            );
        END LOOP;
    END IF;

    RETURN jsonb_build_object('id', new_tree_id);
END;
$$;

-- Trigger to auto-create profile on auth.users insert
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO public.profiles (id, username, role)
    VALUES (NEW.id, NEW.raw_user_meta_data->>'username', 'citizen')
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Trigger to protect user role from self-escalation
CREATE OR REPLACE FUNCTION public.handle_profile_role_protection()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    IF NEW.role IS DISTINCT FROM OLD.role THEN
        IF auth.role() <> 'service_role' AND NOT EXISTS (
            SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'
        ) THEN
            RAISE EXCEPTION 'Only administrators or service role can change user roles';
        END IF;
    END IF;
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_protect_profile_role ON public.profiles;
CREATE TRIGGER trg_protect_profile_role
BEFORE UPDATE ON public.profiles
FOR EACH ROW
EXECUTE FUNCTION public.handle_profile_role_protection();

-- ==============================================================================
-- Row Level Security (RLS) Policies
-- ==============================================================================

ALTER TABLE public.trees ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.photos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.care_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- ------------------------------------------------------------------------------
-- Trees policies
-- 1. Everyone reads trees
-- 2. Only the service role writes imports (city_register, osm)
-- 3. Authenticated citizens can submit citizen trees
-- ------------------------------------------------------------------------------
CREATE POLICY "Trees are readable by everyone"
    ON public.trees FOR SELECT
    USING (true);

CREATE POLICY "Service role can manage all trees"
    ON public.trees FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Authenticated users can insert citizen trees"
    ON public.trees FOR INSERT
    TO authenticated
    WITH CHECK (source = 'citizen' AND status = 'unverified');

-- ------------------------------------------------------------------------------
-- Observations policies
-- 1. Everyone reads observations
-- 2. Signed-in users insert observations
-- 3. Only the author edits (updates or deletes) their own rows
-- ------------------------------------------------------------------------------
CREATE POLICY "Observations are readable by everyone"
    ON public.observations FOR SELECT
    USING (true);

CREATE POLICY "Signed-in users can insert observations"
    ON public.observations FOR INSERT
    TO authenticated
    WITH CHECK (
        auth.uid() IS NOT NULL AND (
            (author IS NULL OR author = auth.uid()) AND
            (author_id IS NULL OR author_id = auth.uid())
        )
    );

CREATE POLICY "Authors can update their own observations"
    ON public.observations FOR UPDATE
    TO authenticated
    USING (author = auth.uid() OR author_id = auth.uid())
    WITH CHECK (author = auth.uid() OR author_id = auth.uid());

CREATE POLICY "Authors can delete their own observations"
    ON public.observations FOR DELETE
    TO authenticated
    USING (author = auth.uid() OR author_id = auth.uid());

CREATE POLICY "Service role has full access to observations"
    ON public.observations FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ------------------------------------------------------------------------------
-- Photos policies
-- 1. Everyone reads verified photos; authors can view their own photos
-- 2. Signed-in users insert photos
-- 3. Only the author edits (updates or deletes) their own rows
-- ------------------------------------------------------------------------------
CREATE POLICY "Verified photos are readable by everyone"
    ON public.photos FOR SELECT
    USING (verified = true OR (auth.uid() IS NOT NULL AND (author = auth.uid() OR author_id = auth.uid())));

CREATE POLICY "Signed-in users can insert photos"
    ON public.photos FOR INSERT
    TO authenticated
    WITH CHECK (
        verified = false AND
        auth.uid() IS NOT NULL AND (
            (author IS NULL OR author = auth.uid()) AND
            (author_id IS NULL OR author_id = auth.uid())
        )
    );

CREATE POLICY "Authors can update their own photos"
    ON public.photos FOR UPDATE
    TO authenticated
    USING (author = auth.uid() OR author_id = auth.uid())
    WITH CHECK (
        verified = false AND
        (author = auth.uid() OR author_id = auth.uid())
    );

CREATE POLICY "Authors can delete their own photos"
    ON public.photos FOR DELETE
    TO authenticated
    USING (author = auth.uid() OR author_id = auth.uid());

CREATE POLICY "Service role has full access to photos"
    ON public.photos FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ------------------------------------------------------------------------------
-- Verifications policies
-- 1. Everyone reads verifications
-- 2. Reviewers (role in profiles) write verifications
-- ------------------------------------------------------------------------------
CREATE POLICY "Verifications are readable by everyone"
    ON public.verifications FOR SELECT
    USING (true);

CREATE POLICY "Reviewers can insert verifications"
    ON public.verifications FOR INSERT
    TO authenticated
    WITH CHECK (public.is_reviewer());

CREATE POLICY "Reviewers can update verifications"
    ON public.verifications FOR UPDATE
    TO authenticated
    USING (public.is_reviewer())
    WITH CHECK (public.is_reviewer());

CREATE POLICY "Reviewers can delete verifications"
    ON public.verifications FOR DELETE
    TO authenticated
    USING (public.is_reviewer());

CREATE POLICY "Service role has full access to verifications"
    ON public.verifications FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ------------------------------------------------------------------------------
-- Care events policies
-- 1. Everyone reads care events
-- 2. Signed-in users insert care events
-- 3. Only the author edits their own rows
-- ------------------------------------------------------------------------------
CREATE POLICY "Care events are readable by everyone"
    ON public.care_events FOR SELECT
    USING (true);

CREATE POLICY "Signed-in users can insert care events"
    ON public.care_events FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() IS NOT NULL AND user_id = auth.uid());

CREATE POLICY "Authors can update their own care events"
    ON public.care_events FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Authors can delete their own care events"
    ON public.care_events FOR DELETE
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Service role has full access to care events"
    ON public.care_events FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ------------------------------------------------------------------------------
-- Profiles policies
-- 1. Everyone reads profiles
-- 2. Users can insert their own profile
-- 3. Users can update their own profile
-- ------------------------------------------------------------------------------
CREATE POLICY "Profiles are readable by everyone"
    ON public.profiles FOR SELECT
    USING (true);

CREATE POLICY "Users can insert their own profile"
    ON public.profiles FOR INSERT
    TO authenticated
    WITH CHECK (id = auth.uid() AND role = 'citizen');

CREATE POLICY "Users can update their own profile"
    ON public.profiles FOR UPDATE
    TO authenticated
    USING (id = auth.uid())
    WITH CHECK (id = auth.uid());

CREATE POLICY "Service role has full access to profiles"
    ON public.profiles FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ==============================================================================
-- Grants
-- ==============================================================================
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL ROUTINES IN SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;

REVOKE ALL ON FUNCTION public.submit_tree_with_observation(JSONB, JSONB, TEXT[]) FROM PUBLIC, anon, service_role;
GRANT EXECUTE ON FUNCTION public.submit_tree_with_observation(JSONB, JSONB, TEXT[]) TO authenticated;
