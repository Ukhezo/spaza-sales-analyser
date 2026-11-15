-- Average sales per day of the week
WITH daily AS (
    SELECT
        DATE(s.sold_at)                                             AS day,
        CAST(STRFTIME('%w', s.sold_at) AS INTEGER)                  AS weekday_num,
        SUM(s.quantity * p.unit_price)                              AS revenue
    FROM sales AS s
    JOIN products AS p USING (product_id)
    GROUP BY day
)
SELECT
    CASE weekday_num
        WHEN 0 THEN 'Sunday'   WHEN 1 THEN 'Monday' WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday' WHEN 4 THEN 'Thursday' WHEN 5 THEN 'Friday'
        ELSE 'Saturday' END                                         AS weekday,
    ROUND(AVG(revenue), 2)                                          AS avg_revenue
FROM daily
GROUP BY weekday_num
ORDER BY avg_revenue DESC;
