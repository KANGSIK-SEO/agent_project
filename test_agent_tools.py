import json
import unittest

from art_forgery_verification_agent import (
    check_condition_and_aging,
    check_pigment_anachronism,
    check_provenance_risk,
    synthesize_risk_score,
)


class AgentToolTests(unittest.TestCase):
    def test_pigment_tool_uses_reference_data(self):
        result = json.loads(
            check_pigment_anachronism.invoke(
                {"artwork_description": "1780년 유럽 유화인데 티타늄 화이트가 검출됐습니다."}
            )
        )

        self.assertEqual(result["tool"], "check_pigment_anachronism")
        self.assertGreaterEqual(result["risk"], 50)
        self.assertTrue(result["sources"])
        self.assertIn("confidence", result)

    def test_condition_and_provenance_results_can_be_synthesized(self):
        condition = json.loads(
            check_condition_and_aging.invoke(
                {"artwork_description": "캔버스는 오래됐지만 새 바니시가 있고 서명만 선명합니다."}
            )
        )
        provenance = json.loads(
            check_provenance_risk.invoke(
                {"provenance_text": "1930년 개인 소장 이후 1985년 경매. 감정서 없음."}
            )
        )

        combined = json.loads(
            synthesize_risk_score.invoke(
                {"tool_results_json": json.dumps([condition, provenance], ensure_ascii=False)}
            )
        )

        self.assertEqual(combined["tool"], "synthesize_risk_score")
        self.assertGreater(combined["risk"], 0)
        self.assertTrue(combined["sources"])


if __name__ == "__main__":
    unittest.main()
