import unittest

from pulse_spatial.experiments.postgis_concurrency import (
    _parse_bytes,
    _resource_summary,
    _statistics_delta,
    parse_pgbench_log,
    percentile,
    summarize_levels,
)


class PostgisConcurrencyTests(unittest.TestCase):
    def test_percentile_interpolates_and_handles_empty_input(self) -> None:
        self.assertIsNone(percentile([], 0.99))
        self.assertEqual(percentile([1.0, 2.0, 3.0], 0.5), 2.0)
        self.assertAlmostEqual(percentile([1.0, 3.0], 0.95), 2.9)

    def test_pgbench_log_parser_preserves_scripts_failures_and_retries(self) -> None:
        parsed = parse_pgbench_log(
            "0 1 1000 0 1 1 0\n1 1 3000 2 1 2 1\n1 2 deadlock 2 1 3 3\n"
        )
        self.assertEqual(parsed["transactions"], 2)
        self.assertEqual(parsed["p50Ms"], 2.0)
        self.assertEqual(parsed["scripts"]["point-membership"]["p99Ms"], 1.0)
        self.assertEqual(parsed["scripts"]["position-update"]["p99Ms"], 3.0)
        self.assertEqual(parsed["failures"], {"deadlock": 1})
        self.assertEqual(parsed["retries"], 4)

    def test_open_loop_log_parser_separates_lag_from_retries(self) -> None:
        parsed = parse_pgbench_log("0 1 2000 0 1 1 1500 2\n")
        self.assertEqual(parsed["scheduleLag"]["p99Ms"], 1.5)
        self.assertEqual(parsed["retries"], 2)
        self.assertEqual(parsed["failures"], {})

    def test_level_summary_reports_variation_without_hiding_runs(self) -> None:
        summary = summarize_levels(
            (
                {
                    "clients": 4,
                    "tps": 100.0,
                    "p99Ms": 2.0,
                    "failures": {},
                    "lateTransactions": 0,
                },
                {
                    "clients": 4,
                    "tps": 120.0,
                    "p99Ms": 4.0,
                    "failures": {},
                    "lateTransactions": 1,
                },
            )
        )
        self.assertEqual(summary[0]["tpsMean"], 110.0)
        self.assertEqual(summary[0]["p99MeanMs"], 3.0)
        self.assertEqual(summary[0]["lateTransactions"], 1)

    def test_telemetry_helpers_preserve_numeric_units_and_deltas(self) -> None:
        self.assertEqual(_parse_bytes("1.5MiB"), 1_572_864)
        self.assertEqual(_parse_bytes("2 GB"), 2_000_000_000)
        self.assertEqual(
            _statistics_delta(
                {"wal": {"wal_bytes": 100, "stats_reset": "before"}},
                {"wal": {"wal_bytes": 260, "stats_reset": "after"}},
            ),
            {"wal": {"wal_bytes": 160}},
        )

    def test_resource_summary_reports_load_and_counter_growth(self) -> None:
        summary = _resource_summary(
            [
                {
                    "cpuPercent": 10.0,
                    "memoryUsedBytes": 100,
                    "memoryPercent": 1.0,
                    "networkReadBytes": 1_000,
                    "networkWriteBytes": 2_000,
                    "blockReadBytes": 3_000,
                    "blockWriteBytes": 4_000,
                    "pids": 5,
                },
                {
                    "cpuPercent": 30.0,
                    "memoryUsedBytes": 200,
                    "memoryPercent": 2.0,
                    "networkReadBytes": 1_500,
                    "networkWriteBytes": 3_000,
                    "blockReadBytes": 3_500,
                    "blockWriteBytes": 5_500,
                    "pids": 7,
                },
            ]
        )
        self.assertEqual(summary["cpuPercentMean"], 20.0)
        self.assertEqual(summary["memoryUsedBytesMax"], 200)
        self.assertEqual(summary["networkWriteBytesDelta"], 1_000)
        self.assertEqual(summary["blockWriteBytesDelta"], 1_500)
        self.assertEqual(summary["pidsMax"], 7)


if __name__ == "__main__":
    unittest.main()
