"""Captured nested Critic reports and cached fourth-round PE recovery, offline."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from critic_harness import qualitative
from planner_harness.common import load,save,sha
from planner_harness.json_output import action_envelope
from planner_harness.model_answers import ModelAnswerUnavailable
from vlm.chatgpt_subscription import ChatGPTSubscriptionVisionModel
from experiments import unified_benchmark as unified
from test_subscription_submission import submission_body
import test_pe_loop as fixtures
import test_unified_results as base
import run_creative_benchmark as cli

CAPTURE=ROOT/'scripts/fixtures/critic-nested-review.txt'


class ReportForms(unittest.TestCase):
    def test_captured_report_is_lossless_and_shared_parser_is_unchanged(self):
        self.assertEqual(sha(CAPTURE),'d31385a3bf1ed8945eacd9068895a8e5e63bdeb11565c5b55f1a3e90564cb2cd')
        value=load(CAPTURE);original=copy.deepcopy(value)
        normalized=qualitative.normalize_action(value)
        self.assertEqual(normalized,{'action':'review','arguments':value['review']})
        self.assertEqual(qualitative.validate(normalized['arguments']),value['review'])
        self.assertEqual(value,original)
        self.assertEqual(action_envelope(value,default_action='review')['arguments'],value)
        for form in (value['review'],{'action':'review','arguments':value['review']},
                     {'action':'review','arguments':value}, {'action':'finish',**value}):
            self.assertEqual(qualitative.normalize_action(form)['arguments'],value['review'])
        with_note={**value,'note':'Observed sky texture.','purpose':'Check paint coverage.'}
        self.assertEqual(qualitative.normalize_action(with_note)['note'],with_note['note'])
        for action in ({'action':'observe','video':'candidate','count':4},
                       {'action':'note','text':'Read the crop.'}):
            self.assertEqual(qualitative.normalize_action(action),action_envelope(action))

    def test_invalid_report_and_ambiguous_wrapper_are_not_silently_accepted(self):
        for value in ({'review':None},{'review':[]},{'review':{}},
                      {'review':{'summary':' '}},{'review':{'summary':'OK','findings':'text'}},
                      {'review':{'summary':'A'},'summary':'B'},
                      {'review':{'summary':'A'},'observe':{'video':'candidate'}}):
            with self.subTest(value=value),self.assertRaises(ValueError):
                qualitative.validate(qualitative.normalize_action(value)['arguments'])


class CachedPEReview(base.Fixture):
    setup_loop=fixtures.PELoopTests.setup_loop
    run_loop=fixtures.PELoopTests.run_loop

    def test_original_command_recovers_fourth_critic_without_resending_and_then_selects(self):
        batch,runtime=self.setup_loop(n=4)
        topic=batch['topics'][0]
        def model(role):
            return ChatGPTSubscriptionVisionModel(role=role,model='openai/gpt-6-luna',
                    reasoning_effort='high',relay_url='http://127.0.0.1:18767')
        runtime.root=self.repo
        runtime.service=SimpleNamespace(model_factory=model)
        def review(*args):
            runtime.calls.append(('review',args[1]['id']))
            return unified.Runtime.review(runtime,*args)
        def choose(*args):
            runtime.calls.append(('choose',len(args[1])))
            return unified.Runtime.choose(runtime,*args)
        runtime.review,runtime.choose=review,choose
        sent=[];critic_calls=0
        def receive(client,request,timeout):
            nonlocal critic_calls
            packet=json.loads(request.data)
            data=json.loads(packet['input'][0]['content'][0]['text'])
            sent.append((client.role,data))
            if client.role=='online_critic':
                critic_calls+=1
                answer=load(CAPTURE) if critic_calls>3 else {'summary':'The blue scene is visible.','findings':[]}
            else:
                selected=data['candidates'][-1]['id']
                refs=[r['id'] for r in data['evidence'] if r['video_id']==selected]
                answer={'selected':selected,'reason':'Prefer this paint treatment.','evidence_refs':refs[:2]}
            response=io.BytesIO(submission_body(json.dumps(answer),packet['model']))
            response.status=200;response.headers={'Content-Type':'text/event-stream'}
            return response
        def old_normalize(value):
            return action_envelope(value,default_action='review',metadata={'note','purpose'})
        with patch.object(ChatGPTSubscriptionVisionModel,'_open',receive), \
             patch.object(qualitative,'normalize_action',side_effect=old_normalize), \
             patch.dict(os.environ,{'LHA_MODEL_FORMAT_ATTEMPTS':'16'}):
            with self.assertRaises(ModelAnswerUnavailable):self.run_loop(batch,runtime)
        folder=self.output/'methods'/topic['id']/'pe-loop'
        self.assertEqual(load(folder/'progress.json')['phase'],'review')
        self.assertEqual(load(folder/'progress.json')['round'],4)
        self.assertEqual(critic_calls,19)  # Three complete reports, original fourth + 15 corrections.
        old_call=folder/'rounds/0004/review/one-shot-critic/calls/review-0001/call'
        before={p:sha(p) for p in (folder/'rounds').rglob('*')
                if p.is_file() and p.name in {'response.txt','input.json','returned.json','video.mp4'} }
        before.update({p:sha(p) for p in (folder/'rounds').glob('*/*.json')})
        save(folder/'settlement.json',{'status':'recovery_required','batch_sha256':load(self.output/'batch.json')['sha256']})
        stdout=io.StringIO()
        with patch.object(sys,'argv',['run_creative_benchmark.py','recover-pe-loop','--output',str(self.output),
                 '--topic',topic['id'],'--reason','Accept the complete saved nested Critic report']), \
             patch('experiments.creative_benchmark.verify_batch',return_value=batch),contextlib.redirect_stdout(stdout):
            cli.main()
        self.assertEqual(json.loads(stdout.getvalue())['model_calls'],0)
        prior=list(runtime.calls);count=len(sent)
        def selection_only(client,request,timeout):
            self.assertEqual(client.role,'planner','Cached Critic must not send another request')
            return receive(client,request,timeout)
        with patch.object(ChatGPTSubscriptionVisionModel,'_open',selection_only):
            result=self.run_loop(batch,runtime)
            self.assertEqual(result['status'],'ready')
            repeated=self.run_loop(batch,runtime)
            self.assertEqual(repeated['status'],'ready')
            self.assertEqual(repeated['entry_sha256'],result['entry_sha256'])
        self.assertEqual(len(sent),count+1)
        self.assertEqual(runtime.calls[len(prior):],[('review','v4'),('choose',4)])
        self.assertEqual(sum(row[0]=='render' for row in runtime.calls),4)
        self.assertTrue(all(sha(p)==digest for p,digest in before.items()))
        selected=load(old_call/'format-recovery/selected.json')
        self.assertEqual(selected['attempt'],0)
        self.assertEqual(Path(selected['response_path']),old_call/'response.txt')
        feedback=load(old_call.parents[2]/'feedback.json')
        self.assertEqual(feedback['report'],load(CAPTURE)['review'])
        self.assertEqual(feedback['review_call'],str(old_call))
        normalized=load(old_call.parent/'normalization.json')
        self.assertEqual(normalized['original'],load(CAPTURE))
        self.assertEqual(normalized['normalized']['arguments'],feedback['report'])


if __name__=='__main__':unittest.main()
