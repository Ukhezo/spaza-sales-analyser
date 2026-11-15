-- Products that sell most differently in winter (May-Aug) vs summer (Nov-Feb)
WITH seasonal AS (
    SELECT
        p.name                                                      AS product,
        SUM(CASE WHEN CAST(STRFTIME('%m', s.sold_at) AS INTEGER) IN (5, 6, 7, 8)
                 THEN s.quantity ELSE 0 END)                        AS winter_units,
        SUM(CASE WHEN CAST(STRFTIME('%m', s.sold_at) AS INTEGER) IN (11, 12, 1, 2)
                 THEN s.quantity ELSE 0 END)                        AS summer_units
    FROM sales AS s
    JOIN products AS p USING (product_id)
    GROUP BY p.product_id
)
SELECT
    product,
    winter_units,
    summer_units,
    ROUND(1.0 * winter_units / summer_units, 2)                     AS winter_to_summer_ratio
FROM seasonal
WHERE summer_units > 0 AND winter_units > 0
-- biggest swing either way: winter-heavy or summer-heavy
ORDER BY MAX(1.0 * winter_units / summer_units, 1.0 * summer_units / winter_units) DESC
LIMIT 6;
