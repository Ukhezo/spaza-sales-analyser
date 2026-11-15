-- How customers pay, and the average value of a sale line per payment method
SELECT
    s.payment_method,
    COUNT(*)                                                        AS sales,
    ROUND(SUM(s.quantity * p.unit_price), 2)                        AS revenue,
    ROUND(AVG(s.quantity * p.unit_price), 2)                        AS avg_sale_value,
    ROUND(100.0 * SUM(s.quantity * p.unit_price)
                / SUM(SUM(s.quantity * p.unit_price)) OVER (), 1)   AS share_pct
FROM sales AS s
JOIN products AS p USING (product_id)
GROUP BY s.payment_method
ORDER BY revenue DESC;
