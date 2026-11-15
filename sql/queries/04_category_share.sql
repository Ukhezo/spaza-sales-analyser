-- Each category's share of sales (SUM() OVER () window function)
SELECT
    p.category,
    ROUND(SUM(s.quantity * p.unit_price), 2)                        AS revenue,
    ROUND(100.0 * SUM(s.quantity * p.unit_price)
                / SUM(SUM(s.quantity * p.unit_price)) OVER (), 1)   AS share_pct,
    ROUND(100.0 * SUM(s.quantity * (p.unit_price - p.unit_cost))
                / SUM(s.quantity * p.unit_price), 1)                AS margin_pct
FROM sales AS s
JOIN products AS p USING (product_id)
GROUP BY p.category
ORDER BY revenue DESC;
