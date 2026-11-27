-- 1
-- closest residential area
WITH nearest_residential_area AS (
	SELECT
	    a.id AS attraction_id,
	    a.name AS attraction,
		a.category AS attraction_category,
	    p.name AS residential_area,
		p.category AS residential_area_category,
		
		ST_Distance(
	        a.geom::geography,
	        p.geom::geography
	    ) / 1000 AS distance_km,
	
	    a.geom AS attraction_geom,
	    p.geom AS residential_area_geom,
	
	    ST_MakeLine(
	        a.geom,
	        p.geom
	    ) AS connection_geom
	
	FROM gold.attractions AS a
	
	CROSS JOIN LATERAL (
	    SELECT *
	    FROM gold.residential_area
	    ORDER BY geom <-> a.geom
	    LIMIT 1
	) AS p
)
SELECT
    *,
    CASE
        WHEN distance_km > 50 THEN 'Far'
        WHEN distance_km > 20 THEN 'Mid'
        ELSE 'Not Far'
    END AS far

FROM nearest_residential_area
LIMIT 100;


--closest accomodations
WITH nearest_accomodations AS (
	SELECT
	    a.id AS attraction_id,
	    a.name AS attraction,
		a.category AS attraction_category,
	    p.name AS accommodations_area,
		p.category AS accommodations_category,
		
		ST_Distance(
	        a.geom::geography,
	        p.geom::geography
	    ) / 1000 AS distance_km,
	
	    a.geom AS attraction_geom,
	    p.geom AS accommodations_geom,
	
	    ST_MakeLine(
	        a.geom,
	        p.geom
	    ) AS connection_geom
	
	FROM gold.attractions AS a
	
	CROSS JOIN LATERAL (
	    SELECT *
	    FROM gold.accommodations
	    ORDER BY geom <-> a.geom
	    LIMIT 1
	) AS p
)

SELECT
    *,
    CASE
        WHEN distance_km > 50 THEN 'Far'
        WHEN distance_km > 20 THEN 'Mid'
        ELSE 'Not Far'
    END AS far

FROM nearest_accomodations
LIMIT 100;



--closest restaurant
WITH nearest_services AS (
    SELECT
        a.id AS attraction_id,
        a.name AS attraction,
        a.category AS attraction_category,

        p.name AS services_area,
        p.category AS services_category,

        ST_Distance(
            a.geom::geography,
            p.geom::geography
        ) / 1000 AS distance_km,

        a.geom AS attraction_geom,
        p.geom AS services_geom,

        ST_MakeLine(
            a.geom,
            p.geom
        ) AS connection_geom

    FROM gold.attractions AS a

    CROSS JOIN LATERAL (
        SELECT *
        FROM gold.services
        ORDER BY geom <-> a.geom
        LIMIT 1
    ) AS p
)

SELECT
    *,
    CASE
        WHEN distance_km > 50 THEN 'Far'
        WHEN distance_km > 20 THEN 'Mid'
        ELSE 'Not Far'
    END AS far

FROM nearest_services
LIMIT 100;



--2.2
SELECT * FROM gold.grid_statistics
ORDER BY total_attractions desc

--2.3
WITH province_geom AS (
    SELECT
        name,
        ST_Transform(
            ST_MakeValid(geom),
            6933
        ) AS geom
    FROM gold.provinces
),

attraction_threshold AS (
    SELECT
        PERCENTILE_CONT(0.75)
        WITHIN GROUP (ORDER BY total_attractions) AS threshold
    FROM gold.grid_statistics
    WHERE total_attractions > 0
),

high_attraction_cells AS (
    SELECT *
    FROM gold.grid_statistics
    WHERE total_attractions >= (
        SELECT threshold FROM attraction_threshold
    )
),

service_ratios AS (
    SELECT
        *,
        100.0 * total_accommodations /
            NULLIF(total_attractions, 0)
            AS accommodations_per_100,

        100.0 * total_restaurants /
            NULLIF(total_attractions, 0)
            AS restaurants_per_100
    FROM high_attraction_cells
),

service_thresholds AS (
    SELECT
        PERCENTILE_CONT(0.25)
            WITHIN GROUP (ORDER BY accommodations_per_100)
            AS accommodation_threshold,

        PERCENTILE_CONT(0.25)
            WITHIN GROUP (ORDER BY restaurants_per_100)
            AS restaurant_threshold
    FROM service_ratios
),

underserved AS (
    SELECT
        sr.*,
        CASE
            WHEN sr.accommodations_per_100 <=
                 st.accommodation_threshold
             AND sr.restaurants_per_100 <=
                 st.restaurant_threshold
                THEN 'Both'

            WHEN sr.accommodations_per_100 <=
                 st.accommodation_threshold
                THEN 'Accommodation shortage'

            ELSE 'Restaurant shortage'
        END AS shortage_type
    FROM service_ratios sr
    CROSS JOIN service_thresholds st
    WHERE
        sr.accommodations_per_100 <=
            st.accommodation_threshold
        OR
        sr.restaurants_per_100 <=
            st.restaurant_threshold
)

SELECT
    u.*,
    p.name AS province_name

FROM underserved u

LEFT JOIN LATERAL (
    SELECT pg.name
    FROM province_geom pg
    WHERE ST_Intersects(u.geom, pg.geom)
    ORDER BY
        ST_Area(ST_Intersection(u.geom, pg.geom)) DESC
    LIMIT 1
) p ON TRUE

ORDER BY u.total_attractions DESC;


--3
--3.1 , 3.2
SELECT
    attr.id AS attraction_id,
    attr.name AS attraction_name,
    ar.id AS accommodation_id,
    ar.name AS accommodation_name

FROM gold.attractions AS attr

INNER JOIN gold.accommodation_range AS ar
    ON ST_Intersects(attr.geom, ar.geom);
	
--3.3
SELECT *
FROM gold.attractions AS attr

WHERE NOT EXISTS (
    SELECT 1
    FROM gold.accommodation_range AS ar
    WHERE ST_Intersects(attr.geom, ar.geom)
);



--3.4.1 - 3.4.2
SELECT
    attr.id AS attraction_id,
    attr.name AS attraction_name,
    rr.id AS restaurant_id,
    rr.name AS restaurant_name

FROM gold.attractions AS attr

INNER JOIN gold.restaurant_range AS rr
    ON ST_Intersects(attr.geom, rr.geom);
	
--3.4.3
SELECT *
FROM gold.attractions AS attr

WHERE NOT EXISTS (
    SELECT 1
    FROM gold.restaurant_range AS rr
    WHERE ST_Intersects(attr.geom, rr.geom)
);


--3.5

WITH attraction_coverage AS (
    SELECT
        attr.id AS attraction_id,
        attr.name AS attraction_name,
        attr.category AS attraction_type,
        attr.geom,

        NOT EXISTS (
            SELECT 1
            FROM gold.accommodation_range ar
            WHERE ST_Intersects(attr.geom, ar.geom)
        ) AS no_accommodation,

        NOT EXISTS (
            SELECT 1
            FROM gold.restaurant_range rr
            WHERE ST_Intersects(attr.geom, rr.geom)
        ) AS no_restaurant

    FROM gold.attractions attr
),

province_assignment AS (
    SELECT
        ac.*,
        p.name AS province_name

    FROM attraction_coverage ac

    LEFT JOIN LATERAL (
        SELECT pr.name
        FROM gold.provinces pr
        WHERE ST_Covers(pr.geom, ac.geom)
        ORDER BY pr.name
        LIMIT 1
    ) p ON TRUE
)

SELECT
    province_name,
    attraction_type,

    COUNT(*) AS total_attractions,

    COUNT(*) FILTER (
        WHERE no_accommodation
    ) AS without_accommodation,

    COUNT(*) FILTER (
        WHERE no_restaurant
    ) AS without_restaurant,

    COUNT(*) FILTER (
        WHERE no_accommodation AND no_restaurant
    ) AS without_both_services,

    ROUND(
        100.0 * COUNT(*) FILTER (WHERE no_accommodation)
        / NULLIF(COUNT(*), 0),
        2
    ) AS accommodation_shortage_percentage,

    ROUND(
        100.0 * COUNT(*) FILTER (WHERE no_restaurant)
        / NULLIF(COUNT(*), 0),
        2
    ) AS restaurant_shortage_percentage

FROM province_assignment

GROUP BY
    province_name,
    attraction_type

ORDER BY
    province_name,
    attraction_type;



