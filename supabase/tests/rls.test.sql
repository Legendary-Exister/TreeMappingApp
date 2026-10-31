BEGIN;
SELECT plan(36);

-- ==============================================================================
-- Setup Test Fixtures (as postgres/superuser)
-- ==============================================================================

-- Create test auth users
INSERT INTO auth.users (id, email, raw_user_meta_data)
VALUES 
    ('11111111-1111-1111-1111-111111111111', 'citizen1@test.com', '{"username": "citizen1"}'),
    ('22222222-2222-2222-2222-222222222222', 'citizen2@test.com', '{"username": "citizen2"}'),
    ('33333333-3333-3333-3333-333333333333', 'reviewer@test.com', '{"username": "reviewer"}'),
    ('44444444-4444-4444-4444-444444444444', 'citizen3@test.com', '{"username": "citizen3"}')
ON CONFLICT (id) DO NOTHING;

-- Exercise the self-service profile policy for a user without an existing profile.
DELETE FROM public.profiles
WHERE id = '44444444-4444-4444-4444-444444444444';

-- Set reviewer role
UPDATE public.profiles
SET role = 'reviewer'
WHERE id = '33333333-3333-3333-3333-333333333333';

SET LOCAL ROLE authenticated;
SET LOCAL "request.jwt.claims" = '{"sub": "44444444-4444-4444-4444-444444444444", "role": "authenticated"}';

SELECT throws_ok(
    $$
    INSERT INTO public.profiles (id, username, role)
    VALUES ('44444444-4444-4444-4444-444444444444', 'self-promoted', 'reviewer')
    $$,
    '42501',
    NULL,
    'RLS: users CANNOT create their own reviewer profile'
);

RESET ROLE;

-- Insert test base tree (Berlin centre: 13.405, 52.520)
INSERT INTO public.trees (
    id,
    geom,
    source,
    source_id,
    licence,
    status,
    genus,
    species,
    leaf_cycle,
    circumference_m,
    height_m
) VALUES (
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    extensions.ST_SetSRID(extensions.ST_MakePoint(13.405, 52.520), 4326)::extensions.geography,
    'city_register',
    'BER-FIXTURE-1',
    'dl-de/by-2-0',
    'verified',
    'Quercus',
    'robur',
    'deciduous',
    2.1,
    18.0
);

-- ==============================================================================
-- 1. Test: trees_near function
-- ==============================================================================
SELECT is(
    (SELECT count(*)::int FROM public.trees_near(13.405, 52.520, 50.0)),
    1,
    'trees_near returns fixture tree within 50m'
);

SELECT is(
    (SELECT count(*)::int FROM public.trees_near(13.500, 52.600, 50.0)),
    0,
    'trees_near returns 0 for far away coordinate'
);

-- ==============================================================================
-- 2. Test: Everyone reads trees
-- ==============================================================================
SET LOCAL ROLE anon;
SET LOCAL "request.jwt.claims" = '{"role": "anon"}';

SELECT is(
    (SELECT count(*)::int FROM public.trees WHERE id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
    1,
    'RLS: anon can read trees'
);

SELECT throws_ok(
    $$
    SELECT public.submit_tree_with_observation(
        '{"latitude": 52.52, "longitude": 13.405}'::jsonb,
        '{"health": "good"}'::jsonb,
        ARRAY[]::text[]
    )
    $$,
    '42501',
    NULL,
    'RLS: anon CANNOT call the citizen tree submission function'
);

SET LOCAL ROLE authenticated;
SET LOCAL "request.jwt.claims" = '{"sub": "11111111-1111-1111-1111-111111111111", "role": "authenticated"}';

SELECT is(
    (SELECT count(*)::int FROM public.trees WHERE id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'),
    1,
    'RLS: authenticated can read trees'
);

-- ==============================================================================
-- 3. Test: Only the service role writes imports
-- ==============================================================================
-- Authenticated citizen tries to insert an imported tree (source = osm or city_register)
SELECT throws_ok(
    $$
    INSERT INTO public.trees (geom, source, source_id, licence)
    VALUES (
        extensions.ST_SetSRID(extensions.ST_MakePoint(13.41, 52.51), 4326)::extensions.geography,
        'osm',
        'osm-node-123',
        'ODbL'
    )
    $$,
    '42501',
    NULL,
    'RLS: authenticated user CANNOT insert imported trees (source=osm)'
);

-- Authenticated citizen CAN insert a citizen tree (source = citizen)
SELECT lives_ok(
    $$
    INSERT INTO public.trees (id, geom, source, source_id, licence)
    VALUES (
        'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        extensions.ST_SetSRID(extensions.ST_MakePoint(13.41, 52.51), 4326)::extensions.geography,
        'citizen',
        'cit-tree-1',
        'CC-BY-4.0'
    )
    $$,
    'RLS: authenticated user CAN insert citizen trees'
);

SELECT throws_ok(
    $$
    INSERT INTO public.trees (geom, source, source_id, licence, status)
    VALUES (
        extensions.ST_SetSRID(extensions.ST_MakePoint(13.41, 52.51), 4326)::extensions.geography,
        'citizen',
        'cit-tree-verified',
        'CC-BY-4.0',
        'verified'
    )
    $$,
    '42501',
    NULL,
    'RLS: citizens CANNOT mark their own trees verified'
);

-- Anon tries to insert a tree (rejected)
SET LOCAL ROLE anon;
SET LOCAL "request.jwt.claims" = '{"role": "anon"}';

SELECT throws_ok(
    $$
    INSERT INTO public.trees (geom, source, source_id, licence)
    VALUES (
        extensions.ST_SetSRID(extensions.ST_MakePoint(13.41, 52.51), 4326)::extensions.geography,
        'citizen',
        'cit-anon-1',
        'CC-BY-4.0'
    )
    $$,
    '42501',
    NULL,
    'RLS: anon user CANNOT insert trees'
);

-- Service role CAN insert imports (source = osm / city_register)
SET LOCAL ROLE service_role;
SET LOCAL "request.jwt.claims" = '{"role": "service_role"}';

SELECT lives_ok(
    $$
    INSERT INTO public.trees (id, geom, source, source_id, licence)
    VALUES (
        'cccccccc-cccc-cccc-cccc-cccccccccccc',
        extensions.ST_SetSRID(extensions.ST_MakePoint(13.42, 52.52), 4326)::extensions.geography,
        'city_register',
        'BER-IMPORT-2',
        'dl-de/by-2-0'
    )
    $$,
    'RLS: service role CAN insert imports'
);

-- ==============================================================================
-- 4. Test: Signed-in users insert observations and photos; anon cannot
-- ==============================================================================
-- Anon tries to insert observation
SET LOCAL ROLE anon;
SET LOCAL "request.jwt.claims" = '{"role": "anon"}';

SELECT throws_ok(
    $$
    INSERT INTO public.observations (tree_id, health, notes)
    VALUES ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'good', 'Anon note')
    $$,
    '42501',
    NULL,
    'RLS: anon user CANNOT insert observations'
);

-- Anon tries to insert photo
SELECT throws_ok(
    $$
    INSERT INTO public.photos (tree_id, photo_url)
    VALUES ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'https://example.com/anon.jpg')
    $$,
    '42501',
    NULL,
    'RLS: anon user CANNOT insert photos'
);

SELECT throws_ok(
    $$
    INSERT INTO public.photos (tree_id, photo_url, verified)
    VALUES ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'https://example.com/forged.jpg', true)
    $$,
    '42501',
    NULL,
    'RLS: anon user CANNOT insert a verified photo'
);

-- Signed-in User 1 inserts observation
SET LOCAL ROLE authenticated;
SET LOCAL "request.jwt.claims" = '{"sub": "11111111-1111-1111-1111-111111111111", "role": "authenticated"}';

SELECT lives_ok(
    $$
    INSERT INTO public.observations (id, tree_id, health, notes, author)
    VALUES (
        '11111111-0000-0000-0000-000000000001',
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'good',
        'User 1 note',
        '11111111-1111-1111-1111-111111111111'
    )
    $$,
    'RLS: authenticated user 1 CAN insert observations'
);

-- Signed-in User 1 inserts an unverified photo
SELECT throws_ok(
    $$
    INSERT INTO public.photos (tree_id, photo_url, verified)
    VALUES ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'https://example.com/forged-authenticated.jpg', true)
    $$,
    '42501',
    NULL,
    'RLS: authenticated users CANNOT insert verified photos'
);

SELECT lives_ok(
    $$
    INSERT INTO public.photos (id, tree_id, photo_url, author, verified)
    VALUES
        ('11111111-0000-0000-0000-000000000002', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'https://example.com/unverified1.jpg', '11111111-1111-1111-1111-111111111111', false)
    $$,
    'RLS: authenticated user 1 CAN insert photos'
);

-- Verified photos may only be created by a trusted server-side writer.
SET LOCAL ROLE service_role;
SET LOCAL "request.jwt.claims" = '{"role": "service_role"}';

INSERT INTO public.photos (id, tree_id, photo_url, author, verified)
VALUES (
    '11111111-0000-0000-0000-000000000003',
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    'https://example.com/verified1.jpg',
    '11111111-1111-1111-1111-111111111111',
    true
);

-- ==============================================================================
-- 5. Test: Everyone reads verified photos; only author reads unverified
-- ==============================================================================
-- Anon reads photos: should see verified photo (3), but NOT unverified (2)
SET LOCAL ROLE anon;
SET LOCAL "request.jwt.claims" = '{"role": "anon"}';

SELECT is(
    (SELECT count(*)::int FROM public.photos WHERE id = '11111111-0000-0000-0000-000000000003'),
    1,
    'RLS: anon CAN read verified photo'
);

SELECT is(
    (SELECT count(*)::int FROM public.photos WHERE id = '11111111-0000-0000-0000-000000000002'),
    0,
    'RLS: anon CANNOT read unverified photo'
);

-- User 2 (non-author) reads photos: should see verified, but NOT unverified of User 1
SET LOCAL ROLE authenticated;
SET LOCAL "request.jwt.claims" = '{"sub": "22222222-2222-2222-2222-222222222222", "role": "authenticated"}';

SELECT is(
    (SELECT count(*)::int FROM public.photos WHERE id = '11111111-0000-0000-0000-000000000002'),
    0,
    'RLS: non-author CANNOT read unverified photo'
);

-- User 1 (author) reads photos: CAN read own unverified photo
SET LOCAL "request.jwt.claims" = '{"sub": "11111111-1111-1111-1111-111111111111", "role": "authenticated"}';

SELECT is(
    (SELECT count(*)::int FROM public.photos WHERE id = '11111111-0000-0000-0000-000000000002'),
    1,
    'RLS: author CAN read own unverified photo'
);

-- ==============================================================================
-- 6. Test: Only author edits their own rows
-- ==============================================================================
-- User 2 tries to update User 1 observation (should update 0 rows)
SET LOCAL "request.jwt.claims" = '{"sub": "22222222-2222-2222-2222-222222222222", "role": "authenticated"}';

UPDATE public.observations
SET notes = 'Hacked by user 2'
WHERE id = '11111111-0000-0000-0000-000000000001';

SELECT is(
    (SELECT notes FROM public.observations WHERE id = '11111111-0000-0000-0000-000000000001'),
    'User 1 note',
    'RLS: non-author CANNOT update another user observation'
);

UPDATE public.photos
SET photo_url = 'https://example.com/hacked.jpg'
WHERE id = '11111111-0000-0000-0000-000000000002';

SET LOCAL "request.jwt.claims" = '{"sub": "11111111-1111-1111-1111-111111111111", "role": "authenticated"}';

SELECT is(
    (SELECT photo_url FROM public.photos WHERE id = '11111111-0000-0000-0000-000000000002'),
    'https://example.com/unverified1.jpg',
    'RLS: non-author CANNOT update another user photo'
);

SELECT throws_ok(
    $$
    UPDATE public.photos
    SET verified = true
    WHERE id = '11111111-0000-0000-0000-000000000002'
    $$,
    '42501',
    NULL,
    'RLS: photo authors CANNOT verify their own photos'
);

UPDATE public.photos
SET photo_url = 'https://example.com/updated.jpg'
WHERE id = '11111111-0000-0000-0000-000000000002';

SELECT is(
    (SELECT photo_url FROM public.photos WHERE id = '11111111-0000-0000-0000-000000000002'),
    'https://example.com/updated.jpg',
    'RLS: photo author CAN update own photo'
);

-- User 2 tries to delete User 1 verified photo (should delete 0 rows)
SET LOCAL "request.jwt.claims" = '{"sub": "22222222-2222-2222-2222-222222222222", "role": "authenticated"}';
DELETE FROM public.photos
WHERE id = '11111111-0000-0000-0000-000000000003';

SELECT is(
    (SELECT count(*)::int FROM public.photos WHERE id = '11111111-0000-0000-0000-000000000003'),
    1,
    'RLS: non-author CANNOT delete another user verified photo'
);

-- User 1 updates own observation (succeeds)
SET LOCAL "request.jwt.claims" = '{"sub": "11111111-1111-1111-1111-111111111111", "role": "authenticated"}';

UPDATE public.observations
SET notes = 'Updated by author'
WHERE id = '11111111-0000-0000-0000-000000000001';

SELECT is(
    (SELECT notes FROM public.observations WHERE id = '11111111-0000-0000-0000-000000000001'),
    'Updated by author',
    'RLS: author CAN update own observation'
);

SELECT throws_ok(
    $$
    UPDATE public.profiles SET role = 'reviewer'
    WHERE id = '11111111-1111-1111-1111-111111111111'
    $$,
    'P0001',
    'Only administrators or service role can change user roles',
    'RLS: users CANNOT promote their own profile'
);

SET LOCAL ROLE anon;
SET LOCAL "request.jwt.claims" = '{"role": "anon"}';

SELECT throws_ok(
    $$
    INSERT INTO public.care_events (tree_id, event_type, notes)
    VALUES ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'watered', 'Anon watering')
    $$,
    '42501',
    NULL,
    'RLS: anon users CANNOT insert care events'
);

SET LOCAL ROLE authenticated;
SET LOCAL "request.jwt.claims" = '{"sub": "11111111-1111-1111-1111-111111111111", "role": "authenticated"}';

SELECT lives_ok(
    $$
    INSERT INTO public.care_events (id, tree_id, event_type, notes)
    VALUES (
        '11111111-0000-0000-0000-000000000004',
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        'watered',
        'User 1 watering'
    )
    $$,
    'RLS: authenticated users CAN insert care events'
);

SET LOCAL "request.jwt.claims" = '{"sub": "22222222-2222-2222-2222-222222222222", "role": "authenticated"}';
UPDATE public.care_events
SET notes = 'Hacked watering'
WHERE id = '11111111-0000-0000-0000-000000000004';

SET LOCAL "request.jwt.claims" = '{"sub": "11111111-1111-1111-1111-111111111111", "role": "authenticated"}';
SELECT is(
    (SELECT notes FROM public.care_events WHERE id = '11111111-0000-0000-0000-000000000004'),
    'User 1 watering',
    'RLS: non-author CANNOT update another user care event'
);

UPDATE public.care_events
SET notes = 'Updated watering'
WHERE id = '11111111-0000-0000-0000-000000000004';

SELECT is(
    (SELECT notes FROM public.care_events WHERE id = '11111111-0000-0000-0000-000000000004'),
    'Updated watering',
    'RLS: care event author CAN update own care event'
);

-- ==============================================================================
-- 7. Test: Reviewers (role in profiles) write verifications
-- ==============================================================================
-- Regular citizen (User 1) tries to write a verification (rejected)
SELECT throws_ok(
    $$
    INSERT INTO public.verifications (tree_id, verdict, notes)
    VALUES ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'approved', 'Citizen trying to verify')
    $$,
    '42501',
    NULL,
    'RLS: regular citizen CANNOT insert verifications'
);

-- Reviewer writes a verification (succeeds)
SET LOCAL "request.jwt.claims" = '{"sub": "33333333-3333-3333-3333-333333333333", "role": "authenticated"}';

SELECT lives_ok(
    $$
    INSERT INTO public.verifications (id, tree_id, reviewer_id, verdict, notes)
    VALUES (
        '33333333-0000-0000-0000-000000000001',
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        '33333333-3333-3333-3333-333333333333',
        'approved',
        'Verified by reviewer'
    )
    $$,
    'RLS: reviewer CAN insert verifications'
);

UPDATE public.verifications
SET notes = 'Updated by reviewer'
WHERE id = '33333333-0000-0000-0000-000000000001';

SELECT is(
    (SELECT notes FROM public.verifications WHERE id = '33333333-0000-0000-0000-000000000001'),
    'Updated by reviewer',
    'RLS: reviewer CAN update verifications'
);

-- ==============================================================================
-- 8. Test: Repeatable imports via unique (source, source_id)
-- ==============================================================================
SET LOCAL ROLE service_role;
SET LOCAL "request.jwt.claims" = '{"role": "service_role"}';

SELECT throws_ok(
    $$
    INSERT INTO public.trees (geom, source, source_id, licence)
    VALUES (
        extensions.ST_SetSRID(extensions.ST_MakePoint(13.405, 52.520), 4326)::extensions.geography,
        'city_register',
        'BER-FIXTURE-1', -- duplicate source_id for city_register
        'dl-de/by-2-0'
    )
    $$,
    '23505', -- unique_violation
    NULL,
    'Unique index on (source, source_id) prevents duplicates'
);

SELECT * FROM finish();
ROLLBACK;
