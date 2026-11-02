"""Offline checks: exact reviewed descriptive modal only; no semantic/model retry."""
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import creative_final_validation as validation
import test_creative_benchmark as fixtures
from test_creative_loop import review_fixture
from planner_harness.common import load,save,sha
from planner_harness.execution import immutable
from critic_harness.one_shot import frozen_profile


class ReviewedJudge:
    model='glm5.3flash';reasoning_effort=None
    calls=0
    def __init__(self,advice=False):type(self).calls=0;self.advice=advice
    def predict_text(self,**kwargs):
        if "source_duration_seconds" in json.loads(kwargs["user_text"]):
            return fixtures.Judge.predict_text(self,**kwargs)
        report=review_fixture(kwargs['user_text'])
        if 'main_scores' not in report:return json.dumps(report)
        type(self).calls+=1
        report['main_scores']['instruction_adherence']['limitations']=['Fixture limit 1.','Fixture limit 2.',validation.SENTENCE]
        if self.advice:report['main_scores']['visual_integrity']['reason']='Use v1 as the input for another pass.'
        return json.dumps(report)


class ValidationTests(unittest.TestCase):
    setUp,tearDown=fixtures.BatchTests.setUp,fixtures.BatchTests.tearDown
    spec=fixtures.BatchTests.spec
    def test_historical_false_positive_passes_current_native_validation(self):
        output=self.root/'batch';topic=self.spec();judge=ReviewedJudge()
        result=validation.cache_judgment(ROOT,output,topic,topic['source_info'],judge=judge)
        self.assertEqual(result['validation_status'],'native_passed')
        self.assertIn(validation.SENTENCE,result['result']['report']['main_scores']['instruction_adherence']['limitations'])
        validation.cache_judgment(ROOT,output,topic,topic['source_info'],judge=judge)
        self.assertEqual(judge.calls,1)

    def test_raw_answer_tampering_is_rejected(self):
        output=self.root/'batch';topic=self.spec();judge=ReviewedJudge()
        result=validation.cache_judgment(ROOT,output,topic,topic['source_info'],judge=judge)
        path=Path(result['path']).parent/'call/response.txt'
        path.write_text(path.read_text()+'changed')
        with self.assertRaises(ValueError):
            validation.cache_judgment(ROOT,output,topic,topic['source_info'],judge=judge)

    def test_independent_judging_has_no_online_advice_gate(self):
        output=self.root/'batch';topic=self.spec();judge=ReviewedJudge(advice=True)
        result=validation.cache_judgment(ROOT,output,topic,topic['source_info'],judge=judge)
        self.assertEqual(result['validation_status'],'native_passed')
        self.assertEqual(judge.calls,1)


if __name__=='__main__':unittest.main()
