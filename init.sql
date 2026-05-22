-- ==========================================================================
-- init.sql — Runs automatically when the postgres container first starts
-- (mounted at /docker-entrypoint-initdb.d/init.sql)
-- ==========================================================================

-- 1. Products reference table (populated by the POS simulator on first run)
CREATE TABLE IF NOT EXISTS products (
    product_id   VARCHAR(50)     PRIMARY KEY,
    product_name VARCHAR(255),
    sector_name  VARCHAR(100),
    unit_price   NUMERIC(10, 2)
);

-- 2. Daily revenue targets per sector
CREATE TABLE IF NOT EXISTS sector_targets (
    sector_name       VARCHAR(100) PRIMARY KEY,
    daily_target_kes  NUMERIC(15, 2)
);

-- 3. Seed targets for all 20 sectors
--    ON CONFLICT ensures re-running this script never errors.
INSERT INTO sector_targets (sector_name, daily_target_kes) VALUES
    ('Maize & Wheat Flour',      400000.00),
    ('Dairy & Milk',             300000.00),
    ('Sugar & Sweeteners',       220000.00),
    ('Cooking Oils & Fats',      280000.00),
    ('Bakery & Pastries',        185000.00),
    ('Cosmetics & Beauty',       350000.00),
    ('Hair Care',                160000.00),
    ('Baby Products',            240000.00),
    ('Butchery & Meat',          520000.00),
    ('Fresh Produce & Groceries',480000.00),
    ('Beverages & Soft Drinks',  310000.00),
    ('Tea & Coffee',             190000.00),
    ('Snacks & Confectionery',   175000.00),
    ('Home Care & Laundry',      210000.00),
    ('Toiletries & Oral Care',   195000.00),
    ('Grains, Pulses & Rice',    370000.00),
    ('Spices & Condiments',      120000.00),
    ('Cereals & Spreads',        155000.00),
    ('Crockery & Housewares',    130000.00),
    ('Electronics & Appliances', 600000.00)
ON CONFLICT (sector_name) DO UPDATE
    SET daily_target_kes = EXCLUDED.daily_target_kes;