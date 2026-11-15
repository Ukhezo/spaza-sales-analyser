-- Payday window (25th to 3rd) vs the rest of the month (CTE + CASE)
WITH daily AS (
    SELECT
        DATE(s.sold_at)                                             AS day,
        CAST(STRFTIME('%d', s.sold_at) AS INTEGER)                  AS day_of_month,
        SUM(s.quantity * p.unit_price)                              AS revenue
    FROM sales AS s
    JOIN products AS p USING (product_id)
    GROUP BY day
)
SELECT
    CASE WHEN day_of_month >= 25 OR day_of_month <= 3
         THEN 'Payday (25th-3rd)' ELSE 'Rest of month' END          AS period,
    COUNT(*)                                                        AS days,
    ROUND(AVG(revenue), 2)                                          AS avg_daily_revenue
FROM daily
GROUP BY period
ORDER BY avg_daily_revenue DESC;
