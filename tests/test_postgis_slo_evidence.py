import unittest

from pulse_spatial.experiments.postgis_slo_evidence import render_markdown


class PostgisSloEvidenceTests(unittest.TestCase):
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
