-- Year-to-date running total of sales at the end of each month
WITH monthly AS (
    SELECT
        STRFTIME('%Y-%m', s.sold_at)                                AS month,
        SUM(s.quantity * p.unit_price)                              AS revenue
    FROM sales AS s
    JOIN products AS p USING (product_id)
    GROUP BY month
)
SELECT
    month,
    ROUND(revenue, 2)                                               AS revenue,
    ROUND(SUM(revenue) OVER (ORDER BY month), 2)                    AS year_to_date
FROM monthly
ORDER BY month;
