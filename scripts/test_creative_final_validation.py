"""Offline checks: exact reviewed descriptive modal only; no semantic/model retry."""
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import creative_final_validation as validation
import test_creative_fewshot as fixtures
from test_creative_loop import review_fixture
from planner_harness.common import load,save,sha
from planner_harness.execution import immutable
from critic_harness.one_shot import frozen_profile


class ReviewedJudge:
    model='glm5.3flash';reasoning_effort=None
    calls=0
    def __init__(self,advice=False):type(self).calls=0;self.advice=advice
    def predict_text(self,**kwargs):
        type(self).calls+=1
        report=review_fixture(kwargs['user_text'])
        report['main_scores']['instruction_adherence']['limitations']=['Fixture limit 1.','Fixture limit 2.',validation.SENTENCE]
        if self.advice:report['main_scores']['visual_integrity']['reason']='Use v1 as the input for another pass.'
        return json.dumps(report)


class ValidationTests(unittest.TestCase):
    setUp,tearDown=fixtures.BatchTests.setUp,fixtures.BatchTests.tearDown
    spec=fixtures.BatchTests.spec
    def rejected(self,advice=False):
        output=self.root/'batch';topic=self.spec();video=topic['source_info'];judge=ReviewedJudge(advice)
        with self.assertRaisesRegex(ValueError,'prohibited action guidance'):
            validation.cache_judgment(ROOT,output,topic,video,judge=judge)
        directory=next((output/'final-judge').glob('*'))
        record={'schema':'lha-supplemental-descriptive-review-v1','disposition':'descriptive_false_positive',
                'review_kind':'agent independent review','reviewer_thread':'offline-fixture-only',
                'field':validation.FIELD,'original_sentence':validation.SENTENCE,'exempted_match':'should',
                'binding':validation.review_binding(directory)}
        save(directory/'supplemental-review/review.json',record)
        return output,topic,video,judge,directory,record

    def test_exact_sentence_retains_original_report_rejection_and_no_new_call(self):
        profile=frozen_profile();output,topic,video,judge,directory,record=self.rejected()
        before=sha(directory/'invalid-report.json');original=json.loads((directory/'call/response.txt').read_text())
        result=validation.cache_judgment(ROOT,output,topic,video,judge=judge)
        self.assertEqual(result['validation_status'],'supplemental_review_passed')
        self.assertEqual(result['result']['report'],original)
        self.assertEqual(sha(directory/'invalid-report.json'),before)
        validation.cache_judgment(ROOT,output,topic,video,judge=judge)
        self.assertEqual(judge.calls,1)
        self.assertEqual(profile,frozen_profile())
        self.assertEqual(load(directory/'supplemental-review/validation.json')['model_calls_added'],0)

    def test_hash_or_field_change_rejects_review_reuse(self):
        output,topic,video,judge,directory,record=self.rejected()
        changed={**record,'field':['main_scores','visual_integrity','limitations',2]}
        save(directory/'supplemental-review/review.json',changed)
        with self.assertRaisesRegex(ValueError,'field, sentence'):validation.cache_judgment(ROOT,output,topic,video,judge=judge)
        save(directory/'supplemental-review/review.json',record)
        with (directory/'call/response.txt').open('a') as stream:stream.write('\n')
        with self.assertRaisesRegex(ValueError,'evidence or identity changed'):validation.cache_judgment(ROOT,output,topic,video,judge=judge)
        self.assertFalse((directory/'judgment.json').exists())

    def test_real_action_guidance_remains_rejected(self):
        output,topic,video,judge,directory,record=self.rejected(advice=True)
        with self.assertRaisesRegex(ValueError,'prohibited action guidance'):
            validation.cache_judgment(ROOT,output,topic,video,judge=judge)
        self.assertFalse((directory/'judgment.json').exists())
        self.assertEqual(judge.calls,1)


if __name__=='__main__':unittest.main()
