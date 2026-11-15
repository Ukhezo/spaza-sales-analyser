-- Headline numbers for the whole year
SELECT
    ROUND(SUM(s.quantity * p.unit_price), 2)                         AS revenue,
    ROUND(SUM(s.quantity * (p.unit_price - p.unit_cost)), 2)         AS gross_profit,
    ROUND(100.0 * SUM(s.quantity * (p.unit_price - p.unit_cost))
                / SUM(s.quantity * p.unit_price), 1)                 AS margin_pct,
    SUM(s.quantity)                                                  AS items_sold,
    COUNT(DISTINCT DATE(s.sold_at))                                  AS trading_days
FROM sales AS s
JOIN products AS p USING (product_id);
