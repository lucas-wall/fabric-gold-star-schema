import duckdb
import pytest
from goldstar.sql import DIM_PROPERTY_DDL, UNKNOWN_SK, fact_bookings_sql, scd2_merge_sql


def load_stage(con, rows):
    con.execute("DROP TABLE IF EXISTS stg_property")
    con.execute("CREATE TABLE stg_property (property_code VARCHAR, property_name VARCHAR, region VARCHAR, effective_ts TIMESTAMP)")
    con.executemany("INSERT INTO stg_property VALUES (?, ?, ?, ?)", rows)
    con.execute(scd2_merge_sql())


@pytest.fixture
def con():
    c = duckdb.connect()
    c.execute(DIM_PROPERTY_DDL)
    load_stage(c, [
        ("CAS-RIO", "Costa Azul Rio", "Southeast", "2026-01-01"),
        ("CAS-BSB", "Costa Azul Brasilia", "Central-West", "2026-01-01"),
    ])
    return c


def versions(con, code):
    return con.execute(
        "SELECT region, is_current, valid_to IS NULL FROM dim_property WHERE property_code = ? ORDER BY valid_from",
        [code],
    ).fetchall()


def test_change_expires_old_version_and_inserts_new_one(con):
    load_stage(con, [
        ("CAS-RIO", "Costa Azul Rio", "Coastal", "2026-06-01"),
        ("CAS-BSB", "Costa Azul Brasilia", "Central-West", "2026-06-01"),
    ])
    assert versions(con, "CAS-RIO") == [("Southeast", False, False), ("Coastal", True, True)]
    assert versions(con, "CAS-BSB") == [("Central-West", True, True)]


def test_rerunning_the_same_stage_is_idempotent(con):
    stage = [("CAS-RIO", "Costa Azul Rio", "Coastal", "2026-06-01")]
    load_stage(con, stage)
    load_stage(con, stage)
    assert con.execute("SELECT COUNT(*) FROM dim_property").fetchone()[0] == 3


def test_fact_gets_the_version_valid_at_booking_time_and_flags_orphans(con):
    load_stage(con, [("CAS-RIO", "Costa Azul Rio", "Coastal", "2026-06-01")])
    con.execute("""
        CREATE TABLE silver_bookings AS SELECT * FROM (VALUES
          ('B-1', 'CAS-RIO', 450.0, 'CHECKED_OUT', TIMESTAMP '2026-03-10 10:00:00'),
          ('B-2', 'CAS-RIO', 300.0, 'BOOKED',      TIMESTAMP '2026-07-02 09:00:00'),
          ('B-3', 'CAS-XXX', 120.0, 'BOOKED',      TIMESTAMP '2026-07-03 09:00:00')
        ) AS v(booking_id, property_code, amount, status, event_ts)""")
    rows = con.execute(f"""
        SELECT f.booking_id, d.region, f.property_sk = '{UNKNOWN_SK}', f.date_key
        FROM ({fact_bookings_sql()}) AS f
        LEFT JOIN dim_property AS d ON d.property_sk = f.property_sk
        ORDER BY f.booking_id""").fetchall()
    assert rows == [
        ("B-1", "Southeast", False, 20260310),
        ("B-2", "Coastal", False, 20260702),
        ("B-3", None, True, 20260703),
    ]
