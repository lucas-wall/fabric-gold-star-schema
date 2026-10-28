"""Gold-layer SQL shared by Spark (Fabric notebooks) and DuckDB (local tests)."""

UNKNOWN_SK = "UNKNOWN"

DIM_PROPERTY_DDL = """
CREATE TABLE IF NOT EXISTS dim_property (
  property_sk STRING, property_code STRING, property_name STRING, region STRING,
  row_hash STRING, valid_from TIMESTAMP, valid_to TIMESTAMP, is_current BOOLEAN
)"""

_HASH = "md5(concat_ws('|', {p}property_name, {p}region))"


def scd2_merge_sql(stage="stg_property", dim="dim_property"):
    # Changed rows appear twice: once to expire the current version (matched),
    # once with a NULL key so the new version is inserted (not matched).
    s_hash = _HASH.format(p="s.")
    return f"""
MERGE INTO {dim} AS t
USING (
  SELECT s.property_code AS merge_key, s.property_code, s.property_name, s.region,
         s.effective_ts, {s_hash} AS row_hash
  FROM {stage} AS s
  UNION ALL
  SELECT NULL AS merge_key, s.property_code, s.property_name, s.region,
         s.effective_ts, {s_hash} AS row_hash
  FROM {stage} AS s
  JOIN {dim} AS d ON d.property_code = s.property_code AND d.is_current
  WHERE d.row_hash <> {s_hash}
) AS u
ON t.property_code = u.merge_key AND t.is_current
WHEN MATCHED AND t.row_hash <> u.row_hash THEN
  UPDATE SET is_current = false, valid_to = u.effective_ts
WHEN NOT MATCHED THEN
  INSERT (property_sk, property_code, property_name, region, row_hash, valid_from, valid_to, is_current)
  VALUES (md5(concat_ws('|', u.property_code, CAST(u.effective_ts AS STRING))),
          u.property_code, u.property_name, u.region, u.row_hash, u.effective_ts, NULL, true)"""


def fact_bookings_sql(silver="silver_bookings", dim="dim_property"):
    # Point-in-time join: each booking gets the property version valid when it happened.
    return f"""
SELECT b.booking_id,
       COALESCE(d.property_sk, '{UNKNOWN_SK}') AS property_sk,
       year(b.event_ts) * 10000 + month(b.event_ts) * 100 + day(b.event_ts) AS date_key,
       b.amount,
       b.status
FROM {silver} AS b
LEFT JOIN {dim} AS d
  ON d.property_code = b.property_code
 AND b.event_ts >= d.valid_from
 AND (d.valid_to IS NULL OR b.event_ts < d.valid_to)"""
