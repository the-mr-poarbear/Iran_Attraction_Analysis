-- Auto-generated Gold-layer DDL adapted dynamically to Silver JSONB schema
CREATE SCHEMA IF NOT EXISTS "gold_jsonb";

DROP TABLE IF EXISTS "gold_jsonb".grid_statistics CASCADE;
DROP TABLE IF EXISTS "gold_jsonb".grid_cells CASCADE;
DROP MATERIALIZED VIEW IF EXISTS "gold_jsonb".accommodation_range CASCADE;
DROP MATERIALIZED VIEW IF EXISTS "gold_jsonb".restaurant_range CASCADE;
DROP MATERIALIZED VIEW IF EXISTS "gold_jsonb".attractions CASCADE;
DROP MATERIALIZED VIEW IF EXISTS "gold_jsonb".accommodations CASCADE;
DROP MATERIALIZED VIEW IF EXISTS "gold_jsonb".residential_area CASCADE;
DROP MATERIALIZED VIEW IF EXISTS "gold_jsonb".services CASCADE;
DROP MATERIALIZED VIEW IF EXISTS "gold_jsonb".provinces CASCADE;
DROP MATERIALIZED VIEW IF EXISTS "gold_jsonb".ways CASCADE;

CREATE MATERIALIZED VIEW "gold_jsonb".attractions AS
SELECT
    ROW_NUMBER() OVER (ORDER BY po."osm_id") AS id,
    po."osm_id" AS osm_id,
    (po."tags" ->> 'name') AS name,
    po."way" AS geom,

    CASE
        WHEN (po."tags" ->> 'natural') IS NOT NULL AND ((po."tags" ->> 'natural') IN ('wood', 'hot_spring')) THEN 'natural'
        WHEN (po."tags" ->> 'historic') IS NOT NULL AND (po."tags" ->> 'tourism') IS NOT NULL THEN 'historic'
        WHEN (po."tags" ->> 'religion') IS NOT NULL AND (po."tags" ->> 'tourism') IS NOT NULL THEN 'religion'
        WHEN (po."tags" ->> 'tourism') IS NOT NULL THEN 'tourism'
        ELSE 'n/a'
    END AS category,

    CASE
        WHEN (po."tags" ->> 'natural') IS NOT NULL AND ((po."tags" ->> 'natural') IN ('wood', 'hot_spring')) THEN (po."tags" ->> 'natural')
        WHEN (po."tags" ->> 'historic') IS NOT NULL AND (po."tags" ->> 'historic') NOT IN ('yes', 'yes;used') AND (po."tags" ->> 'tourism') IS NOT NULL THEN (po."tags" ->> 'historic')
        WHEN (po."tags" ->> 'religion') IS NOT NULL AND (po."tags" ->> 'religion') NOT IN ('none') AND (po."tags" ->> 'tourism') IS NOT NULL THEN (po."tags" ->> 'religion')
        WHEN (po."tags" ->> 'tourism') IS NOT NULL AND (po."tags" ->> 'tourism') NOT IN ('yes') THEN (po."tags" ->> 'tourism')
        ELSE 'n/a'
    END AS subcategory

FROM "silver_jsonb"."planet_osm_point" AS po
WHERE ((po."tags" ->> 'historic') IS NOT NULL OR
    (po."tags" ->> 'religion') IS NOT NULL OR
    (po."tags" ->> 'natural') IS NOT NULL) AND
    ((po."tags" ->> 'tourism') IS NOT NULL AND
    ((po."tags" ->> 'tourism') NOT IN (
        'motel',
        'information',
        'hotel',
        'hostel',
        'guest_house',
        'apartment'
    ))
    OR (po."tags" ->> 'natural') IN ('wood', 'hot_spring')
    );


CREATE MATERIALIZED VIEW "gold_jsonb".accommodations AS
SELECT
    ROW_NUMBER() OVER (ORDER BY po."osm_id") AS id,
    po."osm_id" AS osm_id,
    (po."tags" ->> 'name') AS name,
    po."way" AS geom,
    (po."tags" ->> 'tourism') AS category

FROM "silver_jsonb"."planet_osm_point" AS po
WHERE (po."tags" ->> 'tourism') IN (
        'motel',
        'hotel',
        'hostel',
        'guest_house'
    );


CREATE MATERIALIZED VIEW "gold_jsonb".residential_area AS
SELECT
    ROW_NUMBER() OVER (ORDER BY po."osm_id") AS id,
    po."osm_id" AS osm_id,
    (po."tags" ->> 'name') AS name,
    po."way" AS geom,
    (po."tags" ->> 'place') AS category,
    (po."tags" ->> 'admin_level') AS admin_level

FROM "silver_jsonb"."planet_osm_point" AS po
WHERE (po."tags" ->> 'place') IN (
        'town',
        'village',
        'island',
        'city',
        'suburb'
    );


CREATE MATERIALIZED VIEW "gold_jsonb".services AS
SELECT
    ROW_NUMBER() OVER (ORDER BY po."osm_id") AS id,
    po."osm_id" AS osm_id,
    (po."tags" ->> 'name') AS name,
    po."way" AS geom,
    (po."tags" ->> 'amenity') AS category

FROM "silver_jsonb"."planet_osm_point" AS po
WHERE (po."tags" ->> 'amenity') IN (
    'food_court',
    'cafe',
    'fast_food',
    'restaurant'
    );


CREATE MATERIALIZED VIEW "gold_jsonb".provinces AS
SELECT
    ROW_NUMBER() OVER (ORDER BY po."osm_id") AS id,
    po."osm_id" AS osm_id,
    (po."tags" ->> 'name') AS name,
    po."way" AS geom,
    (po."tags" ->> 'admin_level') AS admin_level

FROM "silver_jsonb"."planet_osm_polygon" AS po
WHERE (po."tags" ->> 'admin_level') = '4';


CREATE MATERIALIZED VIEW "gold_jsonb".ways AS
SELECT
    ROW_NUMBER() OVER (ORDER BY li."osm_id") AS id,
    li."osm_id" AS osm_id,
    (li."tags" ->> 'name') AS name,
    li."way" AS geom,

    CASE
        WHEN li."highway" IS NOT NULL THEN 'highway'
        WHEN (li."tags" ->> 'aerialway') IS NOT NULL THEN 'aerialway'
        WHEN (li."tags" ->> 'railway') IS NOT NULL THEN 'railway'
        WHEN (li."tags" ->> 'junction') IS NOT NULL THEN 'junction'
        WHEN (li."tags" ->> 'tunnel') IS NOT NULL THEN 'tunnel'
        WHEN (li."tags" ->> 'aeroway') IS NOT NULL THEN 'aeroway'
        ELSE 'n/a'
    END AS category

FROM "silver_jsonb"."planet_osm_line" AS li
WHERE (li."tags" ->> 'tunnel') IS NOT NULL
    OR (li."tags" ->> 'railway') IS NOT NULL
    OR (li."tags" ->> 'junction') IS NOT NULL
    OR li."highway" IS NOT NULL
    OR (li."tags" ->> 'aeroway') IS NOT NULL
    OR (li."tags" ->> 'aerialway') IS NOT NULL;


CREATE MATERIALIZED VIEW "gold_jsonb".accommodation_range AS
SELECT
    id,
    osm_id,
    name,
    ST_Buffer(geom::geography, 5000)::geometry AS geom
FROM "gold_jsonb".accommodations;


CREATE MATERIALIZED VIEW "gold_jsonb".restaurant_range AS
SELECT
    id,
    osm_id,
    name,
    ST_Buffer(geom::geography, 5000)::geometry AS geom
FROM "gold_jsonb".services
WHERE category = 'restaurant';


CREATE TABLE "gold_jsonb".grid_cells (
    grid_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    grid_i  INTEGER,
    grid_j  INTEGER,
    geom    GEOMETRY(Polygon, 6933)
);

WITH iran AS (
    SELECT
        ST_Transform(
            ST_MakeValid("way"),
            6933
        ) AS geom
    FROM "silver_jsonb"."planet_osm_polygon"
    WHERE ("tags" ->> 'name') = 'ایران'
),
grid AS (
    SELECT
        s.i,
        s.j,
        s.geom
    FROM iran
    CROSS JOIN LATERAL
        ST_SquareGrid(
            20000,
            ST_Envelope(iran.geom)
        ) AS s
)
INSERT INTO "gold_jsonb".grid_cells (
    grid_i,
    grid_j,
    geom
)
SELECT
    g.i,
    g.j,
    g.geom
FROM grid g
CROSS JOIN iran i
WHERE ST_Intersects(g.geom, i.geom);


CREATE INDEX idx_gold_jsonb_grid_cells_geom
ON "gold_jsonb".grid_cells
USING GIST (geom);


CREATE TABLE "gold_jsonb".grid_statistics AS
WITH attraction_stats AS (
    SELECT
        g.grid_id,
        COUNT(*) AS total_attractions,
        COUNT(*) FILTER (
            WHERE a.category = 'historic'
        ) AS historical_attractions,
        COUNT(*) FILTER (
            WHERE a.category = 'natural'
        ) AS natural_attractions,
        COUNT(*) FILTER (
            WHERE a.category = 'religion'
        ) AS religious_attractions
    FROM "gold_jsonb".grid_cells g
    JOIN "gold_jsonb".attractions a
        ON ST_Intersects(
            g.geom,
            ST_Transform(a.geom, 6933)
        )
    GROUP BY g.grid_id
),
accommodation_stats AS (
    SELECT
        g.grid_id,
        COUNT(*) AS total_accommodations
    FROM "gold_jsonb".grid_cells g
    JOIN "gold_jsonb".accommodations a
        ON ST_Intersects(
            g.geom,
            ST_Transform(a.geom, 6933)
        )
    GROUP BY g.grid_id
),
restaurant_stats AS (
    SELECT
        g.grid_id,
        COUNT(*) AS total_restaurants
    FROM "gold_jsonb".grid_cells g
    JOIN "gold_jsonb".services s
        ON ST_Intersects(
            g.geom,
            ST_Transform(s.geom, 6933)
        )
    WHERE s.category = 'restaurant'
    GROUP BY g.grid_id
)
SELECT
    g.grid_id,
    g.grid_i,
    g.grid_j,
    COALESCE(a.total_attractions, 0) AS total_attractions,
    COALESCE(a.historical_attractions, 0) AS historical_attractions,
    COALESCE(a.natural_attractions, 0) AS natural_attractions,
    COALESCE(a.religious_attractions, 0) AS religious_attractions,
    COALESCE(h.total_accommodations, 0) AS total_accommodations,
    COALESCE(r.total_restaurants, 0) AS total_restaurants,
    g.geom
FROM "gold_jsonb".grid_cells g
LEFT JOIN attraction_stats a
    ON g.grid_id = a.grid_id
LEFT JOIN accommodation_stats h
    ON g.grid_id = h.grid_id
LEFT JOIN restaurant_stats r
    ON g.grid_id = r.grid_id;


CREATE INDEX idx_gold_jsonb_grid_statistics_geom
ON "gold_jsonb".grid_statistics
USING GIST (geom);

CREATE INDEX idx_gold_jsonb_attractions_geom
ON "gold_jsonb".attractions USING GIST (geom);

CREATE INDEX idx_gold_jsonb_attractions_category
ON "gold_jsonb".attractions (category);

CREATE INDEX idx_gold_jsonb_accommodations_geom
ON "gold_jsonb".accommodations USING GIST (geom);

CREATE INDEX idx_gold_jsonb_residential_area_geom
ON "gold_jsonb".residential_area USING GIST (geom);

CREATE INDEX idx_gold_jsonb_services_geom
ON "gold_jsonb".services USING GIST (geom);

CREATE INDEX idx_gold_jsonb_services_category
ON "gold_jsonb".services (category);

CREATE INDEX idx_gold_jsonb_provinces_geom
ON "gold_jsonb".provinces USING GIST (geom);

CREATE INDEX idx_gold_jsonb_ways_geom
ON "gold_jsonb".ways USING GIST (geom);

CREATE INDEX idx_gold_jsonb_restaurant_range_geom
ON "gold_jsonb".restaurant_range USING GIST (geom);

CREATE INDEX idx_gold_jsonb_accommodation_range_geom
ON "gold_jsonb".accommodation_range USING GIST (geom);
