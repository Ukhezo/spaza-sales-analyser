-- Spaza shop sales database (SQLite)
-- Two tables: products holds each item once, sales holds every sale line.

DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS products;

CREATE TABLE products (
    product_id  INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE,
    category    TEXT    NOT NULL,
    unit_price  REAL    NOT NULL CHECK (unit_price >= 0),
    unit_cost   REAL    NOT NULL CHECK (unit_cost >= 0)
);

CREATE TABLE sales (
    sale_id         INTEGER PRIMARY KEY,
    receipt_id      TEXT    NOT NULL,
    sold_at         TEXT    NOT NULL,              -- 'YYYY-MM-DD HH:MM:SS'
    product_id      INTEGER NOT NULL REFERENCES products (product_id),
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    payment_method  TEXT    NOT NULL
);

CREATE INDEX idx_sales_sold_at ON sales (sold_at);
CREATE INDEX idx_sales_product ON sales (product_id);
