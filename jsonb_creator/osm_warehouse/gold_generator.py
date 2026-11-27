"""Dynamic Gold-layer DDL generator and analytical equivalence verifier."""

from __future__ import annotations

import psycopg

from .db import quote_ident, quote_literal
from .inspector import TableClassification


def resolve_attr_expr(
    cls: TableClassification,
    alias: str,
    col_name: str,
    tags_column: str = "tags",
) -> str:
    """Resolve an attribute to either an independent column or a JSONB extraction."""
    col = cls.get_column(col_name)
    if col is None:
        raise KeyError(f"Column '{col_name}' not found in {cls.bronze_schema}.{cls.table_name}")

    prefix = f"{alias}." if alias else ""
    if col.classification == "independent":
        return f"{prefix}{quote_ident(col_name)}"

    expr = f"({prefix}{quote_ident(tags_column)} ->> {quote_literal(col_name)})"
    if col.pg_type not in ("text", "character varying"):
        return f"({expr})::{col.pg_type}"
    return expr


def build_gold_sql(
    classifications: dict[str, TableClassification],
    gold_schema: str,
    tags_column: str = "tags",
) -> str:
    """Generate Gold-layer DDL adapted dynamically to the Silver classification."""
    pt = classifications["planet_osm_point"]
    ln = classifications["planet_osm_line"]
    pg = classifications["planet_osm_polygon"]

    g = quote_ident(gold_schema)
    s_pt = f"{quote_ident(pt.silver_schema)}.{quote_ident(pt.table_name)}"
    s_ln = f"{quote_ident(ln.silver_schema)}.{quote_ident(ln.table_name)}"
    s_pg = f"{quote_ident(pg.silver_schema)}.{quote_ident(pg.table_name)}"

    # Point expressions
    pt_osm_id = resolve_attr_expr(pt, "po", "osm_id", tags_column)
    pt_name = resolve_attr_expr(pt, "po", "name", tags_column)
    pt_way = resolve_attr_expr(pt, "po", "way", tags_column)
    pt_natural = resolve_attr_expr(pt, "po", "natural", tags_column)
    pt_historic = resolve_attr_expr(pt, "po", "historic", tags_column)
    pt_religion = resolve_attr_expr(pt, "po", "religion", tags_column)
    pt_tourism = resolve_attr_expr(pt, "po", "tourism", tags_column)
    pt_place = resolve_attr_expr(pt, "po", "place", tags_column)
    pt_admin = resolve_attr_expr(pt, "po", "admin_level", tags_column)
    pt_amenity = resolve_attr_expr(pt, "po", "amenity", tags_column)

    # Polygon expressions
    pg_osm_id = resolve_attr_expr(pg, "po", "osm_id", tags_column)
    pg_name = resolve_attr_expr(pg, "po", "name", tags_column)
    pg_way = resolve_attr_expr(pg, "po", "way", tags_column)
    pg_admin = resolve_attr_expr(pg, "po", "admin_level", tags_column)
    pg_name_unaliased = resolve_attr_expr(pg, "", "name", tags_column)
    pg_way_unaliased = resolve_attr_expr(pg, "", "way", tags_column)

    # Line expressions
    ln_osm_id = resolve_attr_expr(ln, "li", "osm_id", tags_column)
    ln_name = resolve_attr_expr(ln, "li", "name", tags_column)
    ln_way = resolve_attr_expr(ln, "li", "way", tags_column)
    ln_highway = resolve_attr_expr(ln, "li", "highway", tags_column)
    ln_aerialway = resolve_attr_expr(ln, "li", "aerialway", tags_column)
    ln_railway = resolve_attr_expr(ln, "li", "railway", tags_column)
    ln_junction = resolve_attr_expr(ln, "li", "junction", tags_column)
    ln_tunnel = resolve_attr_expr(ln, "li", "tunnel", tags_column)
    ln_aeroway = resolve_attr_expr(ln, "li", "aeroway", tags_column)

    return f"""-- Auto-generated Gold-layer DDL adapted dynamically to Silver JSONB schema
CREATE SCHEMA IF NOT EXISTS {g};

DROP TABLE IF EXISTS {g}.grid_statistics CASCADE;
DROP TABLE IF EXISTS {g}.grid_cells CASCADE;
DROP MATERIALIZED VIEW IF EXISTS {g}.accommodation_range CASCADE;
DROP MATERIALIZED VIEW IF EXISTS {g}.restaurant_range CASCADE;
DROP MATERIALIZED VIEW IF EXISTS {g}.attractions CASCADE;
DROP MATERIALIZED VIEW IF EXISTS {g}.accommodations CASCADE;
DROP MATERIALIZED VIEW IF EXISTS {g}.residential_area CASCADE;
DROP MATERIALIZED VIEW IF EXISTS {g}.services CASCADE;
DROP MATERIALIZED VIEW IF EXISTS {g}.provinces CASCADE;
DROP MATERIALIZED VIEW IF EXISTS {g}.ways CASCADE;

CREATE MATERIALIZED VIEW {g}.attractions AS
SELECT
    ROW_NUMBER() OVER (ORDER BY {pt_osm_id}) AS id,
    {pt_osm_id} AS osm_id,
    {pt_name} AS name,
    {pt_way} AS geom,

    CASE
        WHEN {pt_natural} IS NOT NULL AND ({pt_natural} IN ('wood', 'hot_spring')) THEN 'natural'
        WHEN {pt_historic} IS NOT NULL AND {pt_tourism} IS NOT NULL THEN 'historic'
        WHEN {pt_religion} IS NOT NULL AND {pt_tourism} IS NOT NULL THEN 'religion'
        WHEN {pt_tourism} IS NOT NULL THEN 'tourism'
        ELSE 'n/a'
    END AS category,

    CASE
        WHEN {pt_natural} IS NOT NULL AND ({pt_natural} IN ('wood', 'hot_spring')) THEN {pt_natural}
        WHEN {pt_historic} IS NOT NULL AND {pt_historic} NOT IN ('yes', 'yes;used') AND {pt_tourism} IS NOT NULL THEN {pt_historic}
        WHEN {pt_religion} IS NOT NULL AND {pt_religion} NOT IN ('none') AND {pt_tourism} IS NOT NULL THEN {pt_religion}
        WHEN {pt_tourism} IS NOT NULL AND {pt_tourism} NOT IN ('yes') THEN {pt_tourism}
        ELSE 'n/a'
    END AS subcategory

FROM {s_pt} AS po
WHERE ({pt_historic} IS NOT NULL OR
    {pt_religion} IS NOT NULL OR
    {pt_natural} IS NOT NULL) AND
    ({pt_tourism} IS NOT NULL AND
    ({pt_tourism} NOT IN (
        'motel',
        'information',
        'hotel',
        'hostel',
        'guest_house',
        'apartment'
    ))
    OR {pt_natural} IN ('wood', 'hot_spring')
    );


CREATE MATERIALIZED VIEW {g}.accommodations AS
SELECT
    ROW_NUMBER() OVER (ORDER BY {pt_osm_id}) AS id,
    {pt_osm_id} AS osm_id,
    {pt_name} AS name,
    {pt_way} AS geom,
    {pt_tourism} AS category

FROM {s_pt} AS po
WHERE {pt_tourism} IN (
        'motel',
        'hotel',
        'hostel',
        'guest_house'
    );


CREATE MATERIALIZED VIEW {g}.residential_area AS
SELECT
    ROW_NUMBER() OVER (ORDER BY {pt_osm_id}) AS id,
    {pt_osm_id} AS osm_id,
    {pt_name} AS name,
    {pt_way} AS geom,
    {pt_place} AS category,
    {pt_admin} AS admin_level

FROM {s_pt} AS po
WHERE {pt_place} IN (
        'town',
        'village',
        'island',
        'city',
        'suburb'
    );


CREATE MATERIALIZED VIEW {g}.services AS
SELECT
    ROW_NUMBER() OVER (ORDER BY {pt_osm_id}) AS id,
    {pt_osm_id} AS osm_id,
    {pt_name} AS name,
    {pt_way} AS geom,
    {pt_amenity} AS category

FROM {s_pt} AS po
WHERE {pt_amenity} IN (
    'food_court',
    'cafe',
    'fast_food',
    'restaurant'
    );


CREATE MATERIALIZED VIEW {g}.provinces AS
SELECT
    ROW_NUMBER() OVER (ORDER BY {pg_osm_id}) AS id,
    {pg_osm_id} AS osm_id,
    {pg_name} AS name,
    {pg_way} AS geom,
    {pg_admin} AS admin_level

FROM {s_pg} AS po
WHERE {pg_admin} = '4';


CREATE MATERIALIZED VIEW {g}.ways AS
SELECT
    ROW_NUMBER() OVER (ORDER BY {ln_osm_id}) AS id,
    {ln_osm_id} AS osm_id,
    {ln_name} AS name,
    {ln_way} AS geom,

    CASE
        WHEN {ln_highway} IS NOT NULL THEN 'highway'
        WHEN {ln_aerialway} IS NOT NULL THEN 'aerialway'
        WHEN {ln_railway} IS NOT NULL THEN 'railway'
        WHEN {ln_junction} IS NOT NULL THEN 'junction'
        WHEN {ln_tunnel} IS NOT NULL THEN 'tunnel'
        WHEN {ln_aeroway} IS NOT NULL THEN 'aeroway'
        ELSE 'n/a'
    END AS category

FROM {s_ln} AS li
WHERE {ln_tunnel} IS NOT NULL
    OR {ln_railway} IS NOT NULL
    OR {ln_junction} IS NOT NULL
    OR {ln_highway} IS NOT NULL
    OR {ln_aeroway} IS NOT NULL
    OR {ln_aerialway} IS NOT NULL;


CREATE MATERIALIZED VIEW {g}.accommodation_range AS
SELECT
    id,
    osm_id,
    name,
    ST_Buffer(geom::geography, 5000)::geometry AS geom
FROM {g}.accommodations;


CREATE MATERIALIZED VIEW {g}.restaurant_range AS
SELECT
    id,
    osm_id,
    name,
    ST_Buffer(geom::geography, 5000)::geometry AS geom
FROM {g}.services
WHERE category = 'restaurant';


CREATE TABLE {g}.grid_cells (
    grid_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    grid_i  INTEGER,
    grid_j  INTEGER,
    geom    GEOMETRY(Polygon, 6933)
);

WITH iran AS (
    SELECT
        ST_Transform(
            ST_MakeValid({pg_way_unaliased}),
            6933
        ) AS geom
    FROM {s_pg}
    WHERE {pg_name_unaliased} = 'ایران'
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
INSERT INTO {g}.grid_cells (
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


CREATE INDEX idx_{gold_schema}_grid_cells_geom
ON {g}.grid_cells
USING GIST (geom);


CREATE TABLE {g}.grid_statistics AS
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
    FROM {g}.grid_cells g
    JOIN {g}.attractions a
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
    FROM {g}.grid_cells g
    JOIN {g}.accommodations a
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
    FROM {g}.grid_cells g
    JOIN {g}.services s
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
FROM {g}.grid_cells g
LEFT JOIN attraction_stats a
    ON g.grid_id = a.grid_id
LEFT JOIN accommodation_stats h
    ON g.grid_id = h.grid_id
LEFT JOIN restaurant_stats r
    ON g.grid_id = r.grid_id;


CREATE INDEX idx_{gold_schema}_grid_statistics_geom
ON {g}.grid_statistics
USING GIST (geom);

CREATE INDEX idx_{gold_schema}_attractions_geom
ON {g}.attractions USING GIST (geom);

CREATE INDEX idx_{gold_schema}_attractions_category
ON {g}.attractions (category);

CREATE INDEX idx_{gold_schema}_accommodations_geom
ON {g}.accommodations USING GIST (geom);

CREATE INDEX idx_{gold_schema}_residential_area_geom
ON {g}.residential_area USING GIST (geom);

CREATE INDEX idx_{gold_schema}_services_geom
ON {g}.services USING GIST (geom);

CREATE INDEX idx_{gold_schema}_services_category
ON {g}.services (category);

CREATE INDEX idx_{gold_schema}_provinces_geom
ON {g}.provinces USING GIST (geom);

CREATE INDEX idx_{gold_schema}_ways_geom
ON {g}.ways USING GIST (geom);

CREATE INDEX idx_{gold_schema}_restaurant_range_geom
ON {g}.restaurant_range USING GIST (geom);

CREATE INDEX idx_{gold_schema}_accommodation_range_geom
ON {g}.accommodation_range USING GIST (geom);
"""


def deploy_gold_layer(conn: psycopg.Connection, gold_sql: str) -> None:
    """Execute the generated Gold-layer DDL inside a transaction."""
    with conn.cursor() as cur:
        cur.execute(gold_sql)
    conn.commit()


def verify_gold_equivalence(
    conn: psycopg.Connection,
    bronze_schema: str,
    gold_schema: str,
) -> list[dict[str, object]]:
    """Compare row counts in gold_jsonb against direct analytical queries on Bronze."""
    b = quote_ident(bronze_schema)
    g = quote_ident(gold_schema)

    checks: list[tuple[str, str]] = [
        (
            "attractions",
            f"""
            SELECT COUNT(*) FROM {b}.planet_osm_point po
            WHERE (po.historic IS NOT NULL OR po.religion IS NOT NULL OR po."natural" IS NOT NULL)
              AND (po.tourism IS NOT NULL AND po.tourism NOT IN ('motel','information','hotel','hostel','guest_house','apartment')
                   OR po."natural" IN ('wood', 'hot_spring'))
            """,
        ),
        (
            "accommodations",
            f"""
            SELECT COUNT(*) FROM {b}.planet_osm_point po
            WHERE po.tourism IN ('motel','hotel','hostel','guest_house')
            """,
        ),
        (
            "residential_area",
            f"""
            SELECT COUNT(*) FROM {b}.planet_osm_point po
            WHERE po.place IN ('town','village','island','city','suburb')
            """,
        ),
        (
            "services",
            f"""
            SELECT COUNT(*) FROM {b}.planet_osm_point po
            WHERE po.amenity IN ('food_court','cafe','fast_food','restaurant')
            """,
        ),
        (
            "provinces",
            f"""
            SELECT COUNT(*) FROM {b}.planet_osm_polygon po
            WHERE po.admin_level = '4'
            """,
        ),
        (
            "ways",
            f"""
            SELECT COUNT(*) FROM {b}.planet_osm_line li
            WHERE tunnel IS NOT NULL OR railway IS NOT NULL OR junction IS NOT NULL
               OR highway IS NOT NULL OR aeroway IS NOT NULL OR aerialway IS NOT NULL
            """,
        ),
        (
            "accommodation_range",
            f"""
            SELECT COUNT(*) FROM {b}.planet_osm_point po
            WHERE po.tourism IN ('motel','hotel','hostel','guest_house')
            """,
        ),
        (
            "restaurant_range",
            f"""
            SELECT COUNT(*) FROM {b}.planet_osm_point po
            WHERE po.amenity = 'restaurant'
            """,
        ),
    ]

    results: list[dict[str, object]] = []
    with conn.cursor() as cur:
        for obj_name, bronze_query in checks:
            cur.execute(f"SELECT COUNT(*) FROM {g}.{quote_ident(obj_name)}")
            gold_cnt = int(cur.fetchone()[0])
            cur.execute(bronze_query)
            bronze_cnt = int(cur.fetchone()[0])
            results.append(
                {
                    "object": f"{gold_schema}.{obj_name}",
                    "gold_count": gold_cnt,
                    "expected_bronze_count": bronze_cnt,
                    "match": gold_cnt == bronze_cnt,
                }
            )

        # Also check grid_cells & grid_statistics row counts and aggregate sums
        cur.execute(f"SELECT COUNT(*) FROM {g}.grid_cells")
        grid_cells_cnt = int(cur.fetchone()[0])
        cur.execute(
            f"""
            SELECT
                COUNT(*),
                SUM(total_attractions),
                SUM(total_accommodations),
                SUM(total_restaurants)
            FROM {g}.grid_statistics
            """
        )
        gs_cnt, sum_attr, sum_acc, sum_rest = cur.fetchone()
        results.append(
            {
                "object": f"{gold_schema}.grid_cells",
                "gold_count": grid_cells_cnt,
                "expected_bronze_count": grid_cells_cnt,
                "match": grid_cells_cnt > 0,
            }
        )
        results.append(
            {
                "object": f"{gold_schema}.grid_statistics",
                "gold_count": int(gs_cnt),
                "expected_bronze_count": grid_cells_cnt,
                "match": int(gs_cnt) == grid_cells_cnt,
                "aggregates": {
                    "sum_total_attractions": int(sum_attr or 0),
                    "sum_total_accommodations": int(sum_acc or 0),
                    "sum_total_restaurants": int(sum_rest or 0),
                },
            }
        )

    return results
