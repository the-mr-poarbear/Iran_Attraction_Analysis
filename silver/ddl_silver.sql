DROP TABLE IF EXISTS silver.planet_osm_line;

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


DROP TABLE IF EXISTS silver.planet_osm_polygon;

CREATE TABLE silver.planet_osm_polygon (
    osm_id      BIGINT,
    way         GEOMETRY(Geometry,4326),
    name        TEXT
);


DROP TABLE IF EXISTS silver.planet_osm_point;

CREATE TABLE silver.planet_osm_point (
    osm_id      BIGINT,
    amenity     TEXT,
    historic    TEXT,
    name        TEXT,
    place       TEXT,
    population  BIGINT,
    religion    TEXT,
    service     TEXT,
    tourism     TEXT,
    way         GEOMETRY(Point, 4326)
);
