-- Monthly sales and profit, with the change from the previous month (LAG window function)
WITH monthly AS (
    SELECT
        STRFTIME('%Y-%m', s.sold_at)                                AS month,
        SUM(s.quantity * p.unit_price)                              AS revenue,
        SUM(s.quantity * (p.unit_price - p.unit_cost))              AS profit
    FROM sales AS s
    JOIN products AS p USING (product_id)
    GROUP BY month
)
SELECT
    month,
    ROUND(revenue, 2)                                               AS revenue,
    ROUND(profit, 2)                                                AS profit,
    ROUND(100.0 * (revenue / LAG(revenue) OVER (ORDER BY month) - 1), 1) AS change_pct
FROM monthly
ORDER BY month;
