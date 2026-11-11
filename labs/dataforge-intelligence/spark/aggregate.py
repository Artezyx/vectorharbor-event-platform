"""Optional Spark batch job over previously validated DataForge event CSV input."""
import argparse
from pyspark.sql import SparkSession, functions as F, types as T

schema = T.StructType([
    T.StructField("event_id", T.StringType(), False),
    T.StructField("tenant_id", T.StringType(), False),
    T.StructField("occurred_at", T.StringType(), False),
    T.StructField("amount", T.StringType(), False),
    T.StructField("currency", T.StringType(), False),
    T.StructField("status", T.StringType(), False),
])


def run(input_path: str, output_path: str) -> None:
    spark = SparkSession.builder.appName("DataForgeRevenue").getOrCreate()
    raw = spark.read.option("header", True).schema(schema).csv(input_path)
    valid = (raw.withColumn("timestamp", F.to_timestamp("occurred_at"))
             .withColumn("amount_num", F.col("amount").cast(T.DecimalType(18, 2)))
             .filter(F.col("timestamp").isNotNull() & F.col("amount_num").isNotNull()
                     & (F.col("amount_num") > 0) & F.col("status").isin("paid", "refunded")
                     & F.col("currency").isin("MXN", "USD"))
             .dropDuplicates(["event_id"]))
    summary = (valid.withColumn("day", F.to_date(F.to_utc_timestamp("timestamp", "UTC")))
               .withColumn("signed_cents",
                           (F.col("amount_num") * F.lit(100) *
                            F.when(F.col("status") == "refunded", -1).otherwise(1)).cast("long"))
               .groupBy("day", "tenant_id", "currency")
               .agg(F.sum("signed_cents").alias("net_cents"),
                    F.sum(F.when(F.col("status") == "paid", 1).otherwise(0)).alias("paid_count"),
                    F.sum(F.when(F.col("status") == "refunded", 1).otherwise(0)).alias("refund_count")))
    summary.write.mode("overwrite").partitionBy("day").parquet(output_path)
    spark.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run(args.input, args.output)
