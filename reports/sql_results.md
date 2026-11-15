# SQL analysis results

Each query lives in [`sql/queries/`](../sql/queries) and runs against the SQLite database built by `spaza_analyser.sql_report`. Tables: `products` (one row per item) and `sales` (one row per sale line).

## Headline numbers for the whole year

[`01_headline_numbers.sql`](../sql/queries/01_headline_numbers.sql)

```sql
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
```

|      revenue |   gross_profit |   margin_pct |   items_sold |   trading_days |
|-------------:|---------------:|-------------:|-------------:|---------------:|
| 1,492,200.89 |     286,606.19 |        19.20 |    79,040.00 |         365.00 |

## Monthly sales and profit, with the change from the previous month (LAG window function)

[`02_monthly_sales.sql`](../sql/queries/02_monthly_sales.sql)

```sql
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
```

| month   |    revenue |    profit |   change_pct |
|:--------|-----------:|----------:|-------------:|
| 2025-01 | 109,380.65 | 21,131.80 |       nan    |
| 2025-02 | 112,901.14 | 21,924.74 |         3.20 |
| 2025-03 | 117,168.54 | 22,432.49 |         3.80 |
| 2025-04 | 119,453.47 | 22,725.27 |         2.00 |
| 2025-05 | 128,962.75 | 24,735.70 |         8.00 |
| 2025-06 | 122,315.21 | 23,099.06 |        -5.20 |
| 2025-07 | 129,486.75 | 25,015.00 |         5.90 |
| 2025-08 | 128,733.44 | 24,830.29 |        -0.60 |
| 2025-09 | 114,188.38 | 21,651.28 |       -11.30 |
| 2025-10 | 118,359.96 | 22,407.91 |         3.70 |
| 2025-11 | 125,079.35 | 24,209.10 |         5.70 |
| 2025-12 | 166,171.25 | 32,443.55 |        32.90 |

## Top 10 products by gross profit

[`03_top_products.sql`](../sql/queries/03_top_products.sql)

```sql
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
```

| product          | category        |   units |    revenue |    profit |
|:-----------------|:----------------|--------:|-----------:|----------:|
| White bread loaf | Bread & bakery  |    8014 | 160,199.86 | 27,968.86 |
| Vetkoek (each)   | Bread & bakery  |    9471 |  47,355.00 | 27,465.90 |
| Maize meal 5kg   | Groceries       |    1444 | 108,285.56 | 17,313.56 |
| Cold drink 2L    | Drinks          |    2638 |  73,837.62 | 17,120.62 |
| Cold drink 500ml | Drinks          |    4468 |  62,507.32 | 16,933.72 |
| Maize meal 10kg  | Groceries       |     789 | 110,452.11 | 16,561.11 |
| Brown bread loaf | Bread & bakery  |    4741 |  85,290.59 | 15,123.79 |
| Chips 125g       | Snacks & sweets |    2995 |  50,885.05 | 13,747.05 |
| Fresh milk 1L    | Dairy & eggs    |    3016 |  69,337.84 | 11,430.64 |
| Sweets (loose)   | Snacks & sweets |   17108 |  17,108.00 |  9,409.40 |

## Each category's share of sales (SUM() OVER () window function)

[`04_category_share.sql`](../sql/queries/04_category_share.sql)

```sql
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
```

| category           |    revenue |   share_pct |   margin_pct |
|:-------------------|-----------:|------------:|-------------:|
| Groceries          | 468,613.49 |       31.40 |        16.40 |
| Bread & bakery     | 292,845.45 |       19.60 |        24.10 |
| Household & energy | 176,034.05 |       11.80 |        20.50 |
| Drinks             | 164,983.48 |       11.10 |        24.20 |
| Dairy & eggs       | 152,014.90 |       10.20 |        16.90 |
| Airtime & data     | 148,082.00 |        9.90 |         6.00 |
| Snacks & sweets    |  89,627.52 |        6.00 |        32.00 |

## Payday window (25th to 3rd) vs the rest of the month (CTE + CASE)

[`05_payday_effect.sql`](../sql/queries/05_payday_effect.sql)

```sql
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
```

| period            |   days |   avg_daily_revenue |
|:------------------|-------:|--------------------:|
| Payday (25th-3rd) |    113 |            5,667.76 |
| Rest of month     |    252 |            3,379.94 |

## Average sales per day of the week

[`06_busiest_weekdays.sql`](../sql/queries/06_busiest_weekdays.sql)

```sql
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
```

| weekday   |   avg_revenue |
|:----------|--------------:|
| Sunday    |      4,740.69 |
| Saturday  |      4,694.80 |
| Friday    |      4,073.11 |
| Thursday  |      3,798.37 |
| Monday    |      3,775.43 |
| Wednesday |      3,773.21 |
| Tuesday   |      3,768.01 |

## The best-selling product (by units) in each category (ROW_NUMBER window function)

[`07_best_seller_per_category.sql`](../sql/queries/07_best_seller_per_category.sql)

```sql
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
```

| category           | product          |   units |
|:-------------------|:-----------------|--------:|
| Snacks & sweets    | Sweets (loose)   |   17108 |
| Bread & bakery     | Vetkoek (each)   |    9471 |
| Drinks             | Cold drink 500ml |    4468 |
| Airtime & data     | Airtime R10      |    3822 |
| Dairy & eggs       | Fresh milk 1L    |    3016 |
| Household & energy | Paraffin 1L      |    1490 |
| Groceries          | Maize meal 5kg   |    1444 |

## Year-to-date running total of sales at the end of each month

[`08_running_total.sql`](../sql/queries/08_running_total.sql)

```sql
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
```

| month   |    revenue |   year_to_date |
|:--------|-----------:|---------------:|
| 2025-01 | 109,380.65 |     109,380.65 |
| 2025-02 | 112,901.14 |     222,281.79 |
| 2025-03 | 117,168.54 |     339,450.33 |
| 2025-04 | 119,453.47 |     458,903.80 |
| 2025-05 | 128,962.75 |     587,866.55 |
| 2025-06 | 122,315.21 |     710,181.76 |
| 2025-07 | 129,486.75 |     839,668.51 |
| 2025-08 | 128,733.44 |     968,401.95 |
| 2025-09 | 114,188.38 |   1,082,590.33 |
| 2025-10 | 118,359.96 |   1,200,950.29 |
| 2025-11 | 125,079.35 |   1,326,029.64 |
| 2025-12 | 166,171.25 |   1,492,200.89 |

## How customers pay, and the average value of a sale line per payment method

[`09_payment_methods.sql`](../sql/queries/09_payment_methods.sql)

```sql
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
```

| payment_method   |   sales |    revenue |   avg_sale_value |   share_pct |
|:-----------------|--------:|-----------:|-----------------:|------------:|
| Cash             |   35291 | 871,315.56 |            24.69 |       58.40 |
| Card             |   13687 | 386,233.86 |            28.22 |       25.90 |
| Mobile wallet    |    8851 | 234,651.47 |            26.51 |       15.70 |

## Products that sell most differently in winter (May-Aug) vs summer (Nov-Feb)

[`10_winter_vs_summer.sql`](../sql/queries/10_winter_vs_summer.sql)

```sql
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
```

| product             |   winter_units |   summer_units |   winter_to_summer_ratio |
|:--------------------|---------------:|---------------:|-------------------------:|
| Teabags 100s        |            285 |            108 |                     2.64 |
| Instant coffee 200g |            147 |             59 |                     2.49 |
| Candles 6s          |            527 |            214 |                     2.46 |
| Matches 10s         |            639 |            294 |                     2.17 |
| Paraffin 1L         |            780 |            364 |                     2.14 |
| Cold drink 500ml    |           1146 |           2161 |                     0.53 |
