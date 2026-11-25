-- =============================================================
-- Stored Procedure: Silver Layer Data Load
-- Purpose: Cleans raw data from Bronze layer into the Silver layer tables
--          of the data warehouse.
--          Existing data is truncated before each load, and
--          execution time is logged for monitoring purposes.
-- Accepts no parameters 
-- Usage: CALL silver.load_silver();
-- =============================================================
CREATE OR REPLACE PROCEDURE silver.load_silver(
	)
LANGUAGE 'plpgsql'
AS $BODY$
DECLARE
    start_time TIMESTAMP;
    end_time TIMESTAMP;
	start_bronze TIMESTAMP;
	end_bronze TIMESTAMP;
BEGIN

    RAISE NOTICE '===============================';
    RAISE NOTICE 'Starting silver layer load...';
    RAISE NOTICE '===============================';

    RAISE NOTICE '--------------------------------';
    RAISE NOTICE 'Loading tables';
    RAISE NOTICE '--------------------------------';

	start_bronze := clock_timestamp();
    start_time := clock_timestamp();
	
	RAISE NOTICE '>> Truncating planet_osm_line';
	TRUNCATE TABLE silver.planet_osm_line;
	RAISE NOTICE '>> Inserting planet_osm_line';
	
	INSERT INTO silver.planet_osm_line (
	    osm_id,
	    aerialway,
	    aeroway,
	    amenity,
	    highway,
	    junction,
	    railway,
	    tunnel,
	    way,
	    name
	)
	SELECT
	    osm_id,
	    -- Aerialway
	    CASE
		    WHEN LOWER(TRIM(aerialway)) IN ('', 'no') THEN NULL
		    ELSE TRIM(aerialway)
		END AS aerialway,
	
	    -- Aeroway
	    CASE
		    WHEN LOWER(TRIM(aeroway)) IN ('', 'no') THEN NULL
		    ELSE TRIM(aeroway)
		END AS aeroway,
	
	    -- Amenity
	    NULLIF(TRIM(amenity), '') AS amenity,
	
	    -- Highway
	    CASE
		    WHEN LOWER(TRIM(highway)) IN ('', 'no') THEN NULL
		    ELSE TRIM(highway)
		END AS highway,
	
	    -- Junction
	    CASE
		    WHEN LOWER(TRIM(junction)) IN ('', 'no') THEN NULL
		    ELSE TRIM(junction)
		END AS junction,
	
	    -- Railway
		CASE
		    WHEN LOWER(TRIM(railway)) IN ('', 'no') THEN NULL
		    ELSE TRIM(railway)
		END AS railway,
	
	    -- Tunnel: preserve valid yes/no values
	    CASE
		    WHEN LOWER(TRIM(tunnel)) IN ('', 'no') THEN NULL
		    ELSE TRIM(tunnel)
		END AS tunnel,
	
	    way,
	    -- Name
	    NULLIF(TRIM(name), '') AS name
	
	FROM public.planet_osm_line;
	end_time := clock_timestamp();
	RAISE NOTICE 'planet_osm_line loaded successfully';
    RAISE NOTICE 'Load Duration: % seconds',
        EXTRACT(EPOCH FROM (end_time - start_time));

	start_time := clock_timestamp();
	RAISE NOTICE '>> Truncating planet_osm_point';
	TRUNCATE TABLE silver.planet_osm_point;
	RAISE NOTICE '>> Inserting planet_osm_point';
	--insert into planet_osm_point silver layer		
	INSERT INTO silver.planet_osm_point (
	    osm_id,
	    amenity,
	    historic,
	    name,
	    place,
	    population,
	    religion,
	    service,
		"natural",
	    tourism,
	    way,
		admin_level
	)
	SELECT
	    p.osm_id,
	    NULLIF(TRIM(p.amenity), ''),
	    NULLIF(TRIM(p.historic), ''),
	    NULLIF(TRIM(p.name), ''),
	    NULLIF(TRIM(p.place), ''),
	    CASE
	        WHEN n.population ~ '^[0-9]+$'
	         AND LENGTH(n.population) <= 18
	        THEN n.population::BIGINT
	        ELSE NULL
	    END,
	    NULLIF(TRIM(p.religion), ''),
	    NULLIF(TRIM(p.service), ''),
		NULLIF(TRIM(p.natural), ''),
	    NULLIF(TRIM(p.tourism), ''),
	    p.way,
		admin_level
	FROM public.planet_osm_point p
	CROSS JOIN LATERAL (
	    SELECT TRANSLATE(
	        REPLACE(
	            REPLACE(
	                REPLACE(
	                    REPLACE(TRIM(p.population), '،', ''),
	                    ',', ''
	                ),
	                '٬', ''
	            ),
	            ' ',
	            ''
	        ),
	        '۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩',
	        '01234567890123456789'
	    ) AS population
	) n;

	end_time := clock_timestamp();

    RAISE NOTICE 'planet_osm_point loaded successfully';
    RAISE NOTICE 'Load Duration: % seconds',
        EXTRACT(EPOCH FROM (end_time - start_time));

	start_time := clock_timestamp();
	RAISE NOTICE '>> Truncating planet_osm_polygon';
	TRUNCATE TABLE silver.planet_osm_polygon;
	RAISE NOTICE '>> Inserting planet_osm_polygon';
	--insert into planet_osm_polygon silver layer
	INSERT INTO silver.planet_osm_polygon(
	    osm_id,
	    name,
		admin_level,
		way
	)
	SELECT
	    osm_id,
	    NULLIF(TRIM(name), '') AS name,
		NULLIF(TRIM(admin_level), '') AS admin_level, 
	    way
	FROM public.planet_osm_polygon;

	end_time := clock_timestamp();

    RAISE NOTICE 'planet_osm_polygon loaded successfully';
    RAISE NOTICE 'Load Duration: % seconds',
        EXTRACT(EPOCH FROM (end_time - start_time));

    RAISE NOTICE '===============================';
    RAISE NOTICE 'Silver layer load completed! Whole process took % seconds' , end_bronze - start_bronze;
    RAISE NOTICE '===============================';

	EXCEPTION
	    WHEN OTHERS THEN
	        RAISE NOTICE '===============================';
	        RAISE NOTICE 'Error: %', SQLERRM;
	        RAISE NOTICE '===============================';
	
	        RAISE;
END;
$BODY$;


