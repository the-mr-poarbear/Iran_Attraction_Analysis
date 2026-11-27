-- Auto-generated Silver-layer JSONB migration SQL

CREATE SCHEMA IF NOT EXISTS "silver_jsonb";


-- === silver_jsonb.planet_osm_point ===

DROP TABLE IF EXISTS "silver_jsonb"."planet_osm_point" CASCADE;
CREATE TABLE "silver_jsonb"."planet_osm_point" (
    "osm_id" bigint,
    "way" geometry(Point,4326),
    "tags" jsonb NOT NULL DEFAULT '{}'::jsonb
);

INSERT INTO "silver_jsonb"."planet_osm_point" ("osm_id", "way", "tags")
SELECT
    src."osm_id",
    src."way",
    COALESCE(
        jsonb_strip_nulls(
            to_jsonb(src) - ARRAY['osm_id', 'way']::text[]
        ),
        '{}'::jsonb
    ) AS "tags"
FROM "public"."planet_osm_point" AS src;

CREATE INDEX "idx_planet_osm_point_way_gist" ON "silver_jsonb"."planet_osm_point" USING GIST ("way");

CREATE INDEX "idx_planet_osm_point_tags_gin" ON "silver_jsonb"."planet_osm_point" USING GIN ("tags");

CREATE INDEX "idx_planet_osm_point_osm_id" ON "silver_jsonb"."planet_osm_point" ("osm_id");

ANALYZE "silver_jsonb"."planet_osm_point";


-- === silver_jsonb.planet_osm_line ===

DROP TABLE IF EXISTS "silver_jsonb"."planet_osm_line" CASCADE;
CREATE TABLE "silver_jsonb"."planet_osm_line" (
    "osm_id" bigint,
    "highway" text,
    "z_order" integer,
    "way" geometry(LineString,4326),
    "tags" jsonb NOT NULL DEFAULT '{}'::jsonb
);

INSERT INTO "silver_jsonb"."planet_osm_line" ("osm_id", "highway", "z_order", "way", "tags")
SELECT
    src."osm_id",
    src."highway",
    src."z_order",
    src."way",
    COALESCE(
        jsonb_strip_nulls(
            to_jsonb(src) - ARRAY['osm_id', 'highway', 'z_order', 'way']::text[]
        ),
        '{}'::jsonb
    ) AS "tags"
FROM "public"."planet_osm_line" AS src;

CREATE INDEX "idx_planet_osm_line_way_gist" ON "silver_jsonb"."planet_osm_line" USING GIST ("way");

CREATE INDEX "idx_planet_osm_line_tags_gin" ON "silver_jsonb"."planet_osm_line" USING GIN ("tags");

CREATE INDEX "idx_planet_osm_line_osm_id" ON "silver_jsonb"."planet_osm_line" ("osm_id");

ANALYZE "silver_jsonb"."planet_osm_line";


-- === silver_jsonb.planet_osm_polygon ===

DROP TABLE IF EXISTS "silver_jsonb"."planet_osm_polygon" CASCADE;
CREATE TABLE "silver_jsonb"."planet_osm_polygon" (
    "osm_id" bigint,
    "building" text,
    "z_order" integer,
    "way_area" real,
    "way" geometry(Geometry,4326),
    "tags" jsonb NOT NULL DEFAULT '{}'::jsonb
);

INSERT INTO "silver_jsonb"."planet_osm_polygon" ("osm_id", "building", "z_order", "way_area", "way", "tags")
SELECT
    src."osm_id",
    src."building",
    src."z_order",
    src."way_area",
    src."way",
    COALESCE(
        jsonb_strip_nulls(
            to_jsonb(src) - ARRAY['osm_id', 'building', 'z_order', 'way_area', 'way']::text[]
        ),
        '{}'::jsonb
    ) AS "tags"
FROM "public"."planet_osm_polygon" AS src;

CREATE INDEX "idx_planet_osm_polygon_way_gist" ON "silver_jsonb"."planet_osm_polygon" USING GIST ("way");

CREATE INDEX "idx_planet_osm_polygon_tags_gin" ON "silver_jsonb"."planet_osm_polygon" USING GIN ("tags");

CREATE INDEX "idx_planet_osm_polygon_osm_id" ON "silver_jsonb"."planet_osm_polygon" ("osm_id");

ANALYZE "silver_jsonb"."planet_osm_polygon";


-- === silver_jsonb.planet_osm_roads ===

DROP TABLE IF EXISTS "silver_jsonb"."planet_osm_roads" CASCADE;
CREATE TABLE "silver_jsonb"."planet_osm_roads" (
    "osm_id" bigint,
    "highway" text,
    "z_order" integer,
    "way" geometry(LineString,4326),
    "tags" jsonb NOT NULL DEFAULT '{}'::jsonb
);

INSERT INTO "silver_jsonb"."planet_osm_roads" ("osm_id", "highway", "z_order", "way", "tags")
SELECT
    src."osm_id",
    src."highway",
    src."z_order",
    src."way",
    COALESCE(
        jsonb_strip_nulls(
            to_jsonb(src) - ARRAY['osm_id', 'highway', 'z_order', 'way']::text[]
        ),
        '{}'::jsonb
    ) AS "tags"
FROM "public"."planet_osm_roads" AS src;

CREATE INDEX "idx_planet_osm_roads_way_gist" ON "silver_jsonb"."planet_osm_roads" USING GIST ("way");

CREATE INDEX "idx_planet_osm_roads_tags_gin" ON "silver_jsonb"."planet_osm_roads" USING GIN ("tags");

CREATE INDEX "idx_planet_osm_roads_osm_id" ON "silver_jsonb"."planet_osm_roads" ("osm_id");

ANALYZE "silver_jsonb"."planet_osm_roads";

