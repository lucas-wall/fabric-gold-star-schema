# Fabric notebook | default lakehouse attached
# silver_bookings + property master -> dim_property (SCD2) + fact_bookings (Direct Lake ready)

from pyspark.sql import functions as F

from goldstar.sql import DIM_PROPERTY_DDL, fact_bookings_sql, scd2_merge_sql

(
    spark.read.option("header", True).csv("Files/reference/property_master.csv")  # noqa: F821
    .withColumn("effective_ts", F.current_timestamp())
    .createOrReplaceTempView("stg_property")
)

spark.sql(DIM_PROPERTY_DDL + " USING DELTA")  # noqa: F821
spark.sql(scd2_merge_sql())  # noqa: F821

spark.sql(fact_bookings_sql()).write.mode("overwrite").saveAsTable("fact_bookings")  # noqa: F821

# V-Order keeps Direct Lake reads fast and cheap on capacity
for table in ("dim_property", "fact_bookings"):
    spark.sql(f"OPTIMIZE {table} VORDER")  # noqa: F821
