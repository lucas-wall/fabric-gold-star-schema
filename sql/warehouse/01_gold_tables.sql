-- Fabric Warehouse | serve gold tables from the lakehouse (cross-database CTAS, full refresh)

IF SCHEMA_ID('gold') IS NULL EXEC('CREATE SCHEMA gold');
GO

DROP TABLE IF EXISTS gold.dim_property;
CREATE TABLE gold.dim_property AS
SELECT property_sk, property_code, property_name, region, valid_from, valid_to, is_current
FROM CostaAzulLakehouse.dbo.dim_property;
GO

DROP TABLE IF EXISTS gold.fact_bookings;
CREATE TABLE gold.fact_bookings AS
SELECT booking_id, property_sk, date_key, amount, status
FROM CostaAzulLakehouse.dbo.fact_bookings;
GO
