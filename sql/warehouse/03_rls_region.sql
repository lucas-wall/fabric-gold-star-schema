-- Fabric Warehouse | row-level security: each manager only sees their region

IF SCHEMA_ID('security') IS NULL EXEC('CREATE SCHEMA security');
GO

CREATE TABLE security.user_region (user_email VARCHAR(256), region VARCHAR(50));
GO

CREATE FUNCTION security.fn_region_access(@region AS VARCHAR(50))
    RETURNS TABLE
WITH SCHEMABINDING
AS
    RETURN SELECT 1 AS allowed
    FROM security.user_region AS ur
    WHERE ur.region = @region AND ur.user_email = USER_NAME();
GO

-- Facts carry no region, so access is resolved through the property dimension
CREATE FUNCTION security.fn_property_access(@property_sk AS VARCHAR(64))
    RETURNS TABLE
WITH SCHEMABINDING
AS
    RETURN SELECT 1 AS allowed
    FROM gold.dim_property AS d
    JOIN security.user_region AS ur ON ur.region = d.region
    WHERE d.property_sk = @property_sk AND ur.user_email = USER_NAME();
GO

CREATE SECURITY POLICY security.region_policy
    ADD FILTER PREDICATE security.fn_region_access(region) ON gold.dim_property,
    ADD FILTER PREDICATE security.fn_property_access(property_sk) ON gold.fact_bookings
WITH (STATE = ON);
GO
