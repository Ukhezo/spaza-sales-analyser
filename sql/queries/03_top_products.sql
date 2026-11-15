-- Top 10 products by gross profit
SELECT
    p.name                                                          AS product,
    p.category,
    SUM(s.quantity)                                                 AS units,
    ROUND(SUM(s.quantity * p.unit_price), 2)                        AS revenue,
    ROUND(SUM(s.quantity * (p.unit_price - p.unit_cost)), 2)        AS profit
FROM sales AS s
JOIN products AS p USING (product_id)
GROUP BY p.product_id
ORDER BY profit DESC
LIMIT 10;
