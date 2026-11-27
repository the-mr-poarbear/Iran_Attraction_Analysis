DROP MATERIALIZED VIEW IF EXISTS gold.attractions;
CREATE MATERIALIZED VIEW gold.attractions AS
SELECT 
    ROW_NUMBER() OVER (ORDER BY po.osm_id) AS id,
    po.osm_id,
    po.name,
    po.way AS geom,

	CASE
		WHEN po.natural IS NOT NULL AND (po.natural IN ('wood', 'hot_spring')) THEN 'natural'
        WHEN po.historic IS NOT NULL AND po.tourism IS NOT NULL THEN 'historic'
		WHEN po.religion IS NOT NULL AND  po.tourism IS NOT NULL THEN 'religion'
        WHEN po.tourism IS NOT NULL THEN 'tourism'
        ELSE 'n/a'
    END AS category,

    CASE
		WHEN po.natural IS NOT NULL AND (po.natural IN ('wood', 'hot_spring')) THEN po.natural
        WHEN po.historic IS NOT NULL AND po.historic NOT IN ('yes', 'yes;used') AND po.tourism IS NOT NULL THEN po.historic
		WHEN po.religion IS NOT NULL AND po.religion NOT IN ('none') AND po.tourism IS NOT NULL THEN po.religion
        WHEN po.tourism IS NOT NULL AND  po.tourism NOT IN ('yes') THEN po.tourism
        ELSE 'n/a'
    END AS subcategory
	
FROM silver.planet_osm_point AS po
WHERE (po.historic IS NOT NULL OR 
	po.religion IS NOT NULL OR 
	po.natural IS NOT NULL) AND 
	(po.tourism IS NOT NULL AND 
	(po.tourism NOT IN (
        'motel',
        'information',
        'hotel',
        'hostel',
        'guest_house',
        'apartment'
    ))
	OR po.natural IN ('wood', 'hot_spring')
	);
	

DROP MATERIALIZED VIEW IF EXISTS gold.accommodations;
CREATE MATERIALIZED VIEW gold.accommodations AS
SELECT 
    ROW_NUMBER() OVER (ORDER BY po.osm_id) AS id,
    po.osm_id,
    po.name,
    po.way AS geom,
    po.tourism AS category
	
FROM silver.planet_osm_point AS po
WHERE po.tourism IN (
        'motel',
        'hotel',
        'hostel',
        'guest_house'
    );


DROP MATERIALIZED VIEW IF EXISTS gold.residential_area;
CREATE MATERIALIZED VIEW gold.residential_area AS
SELECT 
    ROW_NUMBER() OVER (ORDER BY po.osm_id) AS id,
    po.osm_id,
    po.name,
    po.way AS geom,
    po.place AS category,
	po.admin_level
	
FROM silver.planet_osm_point AS po
WHERE po.place IN (
        'town',
        'village',
        'island',
        'city',
        'suburb'
    );


DROP MATERIALIZED VIEW IF EXISTS gold.services;
CREATE MATERIALIZED VIEW gold.services AS
SELECT 
    ROW_NUMBER() OVER (ORDER BY po.osm_id) AS id,
    po.osm_id,
    po.name,
    po.way AS geom,
    po.amenity AS category
	
FROM silver.planet_osm_point AS po
WHERE po.amenity IN (
	'food_court',
	'cafe',
	'fast_food',
	'restaurant'
    );

DROP MATERIALIZED VIEW IF EXISTS gold.provinces;
CREATE MATERIALIZED VIEW gold.provinces AS
SELECT 
    ROW_NUMBER() OVER (ORDER BY po.osm_id) AS id,
    po.osm_id,
    po.name,
    po.way AS geom,
	po.admin_level

	
FROM silver.planet_osm_polygon AS po
WHERE po.admin_level ='4';

DROP MATERIALIZED VIEW IF EXISTS gold.ways;
CREATE MATERIALIZED VIEW gold.ways AS
SELECT 
    ROW_NUMBER() OVER (ORDER BY li.osm_id) AS id,
    li.osm_id,
    li.name,
    li.way AS geom,

	CASE
        WHEN li.highway IS NOT NULL THEN 'highway'
		WHEN li.aerialway IS NOT NULL THEN 'aerialway'
        WHEN li.railway IS NOT NULL THEN 'railway'
		WHEN li.junction IS NOT NULL THEN 'junction'
		WHEN li.tunnel IS NOT NULL THEN 'tunnel'
        WHEN li.aeroway IS NOT NULL THEN 'aeroway'
        ELSE 'n/a'
    END AS category
	
FROM silver.planet_osm_line AS li
WHERE tunnel IS NOT NULL
	OR railway IS NOT NULL 
	OR junction IS NOT NULL 
	OR highway IS NOT NULL 
	OR aeroway IS NOT NULL 
	OR aerialway IS NOT NULL;


DROP MATERIALIZED VIEW IF EXISTS gold.accommodation_range CASCADE;

CREATE MATERIALIZED VIEW gold.accommodation_range AS
SELECT
    id,
    osm_id,
    name,
    ST_Buffer(geom::geography, 5000)::geometry AS geom
FROM gold.accommodations;


DROP MATERIALIZED VIEW IF EXISTS gold.restaurant_range CASCADE;

CREATE MATERIALIZED VIEW gold.restaurant_range AS
SELECT
    id,
    osm_id,
    name,
    ST_Buffer(geom::geography, 5000)::geometry AS geom
FROM gold.services
WHERE category = 'restaurant';


DROP TABLE IF EXISTS gold.grid_cells;
CREATE TABLE gold.grid_cells (
    grid_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    grid_i  INTEGER,
    grid_j  INTEGER,
    geom    GEOMETRY(Polygon, 6933)
);

WITH iran AS (
    SELECT
        ST_Transform(
            ST_MakeValid(way),
            6933
        ) AS geom
    FROM public.planet_osm_polygon
    WHERE name = 'ایران'
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
INSERT INTO gold.grid_cells (
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


CREATE INDEX idx_grid_cells_geom
ON gold.grid_cells
USING GIST (geom);


DROP TABLE IF EXISTS gold.grid_statistics;
CREATE TABLE gold.grid_statistics AS

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

    FROM gold.grid_cells g
    JOIN gold.attractions a
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

    FROM gold.grid_cells g
    JOIN gold.accommodations a
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

    FROM gold.grid_cells g
    JOIN gold.services s
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

    COALESCE(a.total_attractions, 0)
        AS total_attractions,

    COALESCE(a.historical_attractions, 0)
        AS historical_attractions,

    COALESCE(a.natural_attractions, 0)
        AS natural_attractions,

    COALESCE(a.religious_attractions, 0)
        AS religious_attractions,

    COALESCE(h.total_accommodations, 0)
        AS total_accommodations,

    COALESCE(r.total_restaurants, 0)
        AS total_restaurants,

    g.geom

FROM gold.grid_cells g

LEFT JOIN attraction_stats a
    ON g.grid_id = a.grid_id

LEFT JOIN accommodation_stats h
    ON g.grid_id = h.grid_id

LEFT JOIN restaurant_stats r
    ON g.grid_id = r.grid_id;


CREATE INDEX idx_grid_statistics_geom
ON gold.grid_statistics
USING GIST (geom);

-- Attractions
CREATE INDEX idx_attractions_geom
ON gold.attractions USING GIST (geom);

CREATE INDEX idx_attractions_category
ON gold.attractions (category);


-- Accommodations
CREATE INDEX idx_accommodations_geom
ON gold.accommodations USING GIST (geom);


-- Residential areas
CREATE INDEX idx_residential_area_geom
ON gold.residential_area USING GIST (geom);


-- Services
CREATE INDEX idx_services_geom
ON gold.services USING GIST (geom);

CREATE INDEX idx_services_category
ON gold.services (category);


-- Provinces
CREATE INDEX idx_provinces_geom
ON gold.provinces USING GIST (geom);


-- Ways
CREATE INDEX idx_ways_geom
ON gold.ways USING GIST (geom);

CREATE INDEX idx_restaurant_range_geom
ON gold.restaurant_range USING GIST (geom);

CREATE INDEX idx_accommodation_range_geom
ON gold.accommodation_range USING GIST (geom);

