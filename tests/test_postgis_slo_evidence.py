import json
import tempfile
import unittest
from pathlib import Path

from pulse_spatial.experiments.postgis_slo_evidence import consolidate, render_markdown


class PostgisSloEvidenceTests(unittest.TestCase):
    @staticmethod
    def _result(target: int, passed: bool, transactions: int = 100) -> dict:
        protocol = {
            "clients": 96,
            "warmupSecondsPerRate": 10,
            "measurementSecondsPerRate": 60,
            "repetitions": 3,
            "latencyLimitMs": 20,
            "admissionLatencyLimitMs": 100,
            "maximumSkipRate": 0.001,
            "deviceCount": 50000,
            "scriptWeights": "position=7,range=3",
            "stateResetPerMeasuredRun": True,
            "loadGeneratorPlacement": "separate-container",
        }
        summary = {
            "targetTps": target,
            "reportedTpsMean": float(target - 1),
            "p99MaxMs": 10.0 if passed else 30.0,
            "skipRateMax": 0.0,
            "transactionFailures": 0,
            "allSloPass": passed,
        }
        return {
            "experiment": "postgis-open-loop-slo-saturation-v1",
            "protocol": protocol,
            "summaryByRate": [summary],
            "levels": [{"transactions": transactions}],
            "environment": {"database": "PostgreSQL"},
            "dataset": {"name": "fixture"},
        }

    def test_consolidate_preserves_contiguous_lower_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for target, passed in ((10000, True), (12000, False), (14000, True)):
                path = root / f"{target}.json"
                path.write_text(
                    json.dumps(self._result(target, passed)), encoding="utf-8"
                )
                paths.append(path)

            result = consolidate(paths)

        self.assertEqual(
            result["capacity"]["conservativeRepeatedWindowLowerBoundTps"], 10000
        )
        self.assertEqual(result["capacity"]["firstFailedTargetTps"], 12000)
        self.assertEqual(
            result["capacity"]["isolatedPassingTargetsAfterFailureTps"], [14000]
        )
        self.assertEqual(result["repeatedWindowTransactions"], 300)

    def test_markdown_handles_no_failed_target(self) -> None:
        rendered = render_markdown(
            {
                "capacity": {
                    "conservativeRepeatedWindowLowerBoundTps": 5000,
                    "firstFailedTargetTps": None,
                },
                "protocol": {
                    "latencyLimitMs": 20,
                    "admissionLatencyLimitMs": 100,
                    "maximumSkipRate": 0.001,
                },
                "repeatedWindowTransactions": 100,
                "maximumObservedCompletionTps": 5000.0,
                "repeatedWindowSummary": [],
                "sustainedFiveMinuteSummary": [],
                "decisionRule": "contiguous prefix",
            }
        )
        self.assertIn("not observed", rendered)

    def test_markdown_keeps_conservative_and_isolated_results_distinct(self) -> None:
        rendered = render_markdown(
            {
                "capacity": {
                    "conservativeRepeatedWindowLowerBoundTps": 5000,
                    "firstFailedTargetTps": 5500,
                },
                "protocol": {"latencyLimitMs": 20, "maximumSkipRate": 0.001},
                "repeatedWindowTransactions": 100,
                "maximumObservedCompletionTps": 20000.0,
                "repeatedWindowSummary": [
                    {
                        "targetTps": 5000,
                        "reportedTpsMean": 4990.0,
                        "p99MaxMs": 6.0,
                        "skipRateMax": 0.0005,
                        "transactionFailures": 0,
                        "allSloPass": True,
                    }
                ],
                "sustainedFiveMinuteSummary": [],
                "decisionRule": "contiguous prefix",
            }
        )
        self.assertIn("5,000 TPS", rendered)
        self.assertIn("20,000.00 TPS", rendered)
        self.assertIn("contiguous prefix", rendered)


if __name__ == "__main__":
    unittest.main()
