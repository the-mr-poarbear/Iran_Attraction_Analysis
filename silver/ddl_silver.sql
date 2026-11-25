DROP TABLE  IF EXISTS silver.planet_osm_line CASCADE;

CREATE TABLE silver.planet_osm_line (
    osm_id      BIGINT,
    aerialway   TEXT,
    aeroway     TEXT,
    amenity     TEXT,
    highway     TEXT,
    junction    TEXT,
    railway     TEXT,
    tunnel      TEXT,
    way         GEOMETRY(LineString, 4326),
    name        TEXT
);


DROP TABLE IF EXISTS silver.planet_osm_polygon CASCADE;

CREATE TABLE silver.planet_osm_polygon (
    osm_id      BIGINT,
	admin_level TEXT,
    way         GEOMETRY(Geometry,4326),
    name        TEXT
);


DROP TABLE IF EXISTS silver.planet_osm_point CASCADE;

CREATE TABLE silver.planet_osm_point (
    osm_id      BIGINT,
    amenity     TEXT,
    historic    TEXT,
    name        TEXT,
    place       TEXT,
    population  BIGINT,
    religion    TEXT,
    service     TEXT,
	"natural"   TEXT,
    tourism     TEXT,
    way         GEOMETRY(Point, 4326),
	admin_level TEXT
);




CREATE INDEX idx_silver_point_attractions_geom
ON silver.planet_osm_point
USING GIST (way)
WHERE
    historic IS NOT NULL
    OR religion IS NOT NULL
    OR tourism IS NOT NULL;



CREATE INDEX idx_silver_point_accommodations_geom
ON silver.planet_osm_point
USING GIST (way)
WHERE
    tourism IN (
        'motel',
        'hotel',
        'hostel',
        'guest_house'
    );



CREATE INDEX idx_silver_point_residential_geom
ON silver.planet_osm_point
USING GIST (way)
WHERE
    place IN (
        'town',
        'village',
        'island',
        'city',
        'suburb'
    );



CREATE INDEX idx_silver_point_services_geom
ON silver.planet_osm_point
USING GIST (way)
WHERE
    amenity IN (
        'food_court',
        'cafe',
        'fast_food',
        'restaurant'
    );



CREATE INDEX idx_silver_polygon_provinces_geom
ON silver.planet_osm_polygon
USING GIST (way);
