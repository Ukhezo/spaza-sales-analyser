-- The best-selling product (by units) in each category (ROW_NUMBER window function)
WITH ranked AS (
    SELECT
        p.category,
        p.name                                                      AS product,
        SUM(s.quantity)                                             AS units,
        ROW_NUMBER() OVER (PARTITION BY p.category ORDER BY SUM(s.quantity) DESC) AS rank_in_category
    FROM sales AS s
    JOIN products AS p USING (product_id)
    GROUP BY p.product_id
)
SELECT category, product, units
FROM ranked
WHERE rank_in_category = 1
ORDER BY units DESC;
