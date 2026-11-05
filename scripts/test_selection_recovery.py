"""Repair actual PE citation failures in the original selection step, offline."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from planner_harness import accounting
from planner_harness.common import load, save, sha
from planner_harness.model_answers import ModelAnswerUnavailable
from planner_harness.model_call import call_text
from planner_harness.video import Video
from vlm.chatgpt_subscription import ChatGPTSubscriptionVisionModel
from experiments import unified_benchmark as unified
import test_pe_loop as fixtures
import test_unified_results as base
from test_subscription_submission import submission_body

BAD_REFS=['source:overview-1:0','source:overview-1:5','candidate:overview-2:0',
          'candidate:overview-2:3','candidate:overview-2:6','candidate:overview-2:8']


class SelectionRecovery(base.Fixture):
    setup_loop=fixtures.PELoopTests.setup_loop
    run_loop=fixtures.PELoopTests.run_loop

    def model(self):
        return ChatGPTSubscriptionVisionModel(role='planner',model='openai/gpt-6-luna',
                                             reasoning_effort='high',relay_url='http://127.0.0.1:18767')

    def transport(self, sent, *, invalid_count=3, always_invalid=False):
        def receive(client,request,timeout):
            packet=json.loads(request.data)
            data=json.loads(packet['input'][0]['content'][0]['text'])
            correction='original_input' in data
            original=json.loads(data['original_input']) if correction else data
            selected=original['candidates'][-1]['id']
            refs=[row['id'] for row in original['evidence'] if row['video_id']==selected]
            invalid=always_invalid or (len(original['candidates'])==invalid_count and not correction)
            answer={'selected':selected,'reason':'This candidate best realizes the requested blue treatment.',
                    'evidence_refs':BAD_REFS if invalid else refs[:2]}
            sent.append({'packet':packet,'input':data,'answer':answer,'correction':correction})
            response=io.BytesIO(submission_body(json.dumps(answer),packet['model']))
            response.status=200;response.headers={'Content-Type':'text/event-stream'}
            return response
        return receive

    def selection_inputs(self):
        video=Video(self.source,self.root/'source-info').info
        topic={'source_info':video,'request':'Make the scene blue.'}
        candidates=[{'video':video} for _ in range(3)]
        reviews=[{'report':{'summary':'Blue is visible.',
            'findings':[{'evidence_refs':['candidate:overview-2:0']}]}} for _ in candidates]
        return topic,candidates,reviews

    def test_captured_wrong_namespace_is_corrected_by_model_and_receipt_tracks_answer(self):
        topic,candidates,reviews=self.selection_inputs();sent=[];directory=self.root/'selection'
        # Save exactly the pre-fix call_text path, before a validator rejected it.
        def old_call(directory,model,system,user,images,**kwargs):
            raw=call_text(directory,model,system,user,images)
            kwargs['validate'](json.loads(raw))
            raise AssertionError('The old citation must be invalid')
        with patch.object(ChatGPTSubscriptionVisionModel,'_open',self.transport(sent)), \
             patch('planner_harness.model_answers.call_object',side_effect=old_call):
            with self.assertRaisesRegex(ValueError,'supplied chosen-candidate evidence'):
                unified.qualitative_select(ROOT,topic,candidates,reviews,directory,self.model())
        original={directory/'call'/name:sha(directory/'call'/name) for name in ('input.json','response.txt','returned.json')}
        with patch.object(ChatGPTSubscriptionVisionModel,'_open',self.transport(sent)):
            index,decision=unified.qualitative_select(ROOT,topic,candidates,reviews,directory,self.model())
            self.assertEqual(unified.qualitative_select(ROOT,topic,candidates,reviews,directory,self.model()),(index,decision))
        self.assertEqual(index,2);self.assertEqual(len(sent),2)
        self.assertTrue(sent[-1]['correction'])
        self.assertEqual(json.loads(sent[-1]['input']['previous_response'])['evidence_refs'],BAD_REFS)
        self.assertTrue(all(sha(path)==digest for path,digest in original.items()))
        receipt=decision['response_call']
        self.assertTrue(receipt['response_path'].endswith('format-recovery/01/call/response.txt'))
        self.assertEqual(decision['response_sha256'],sha(receipt['response_path']))
        self.assertEqual(decision['reason'],sent[0]['answer']['reason'])
        self.assertEqual(decision['evidence_refs'],sent[-1]['answer']['evidence_refs'])

    def test_invalid_references_remain_invalid_when_correction_window_exhausts(self):
        topic,candidates,reviews=self.selection_inputs();sent=[];directory=self.root/'invalid'
        with patch.object(ChatGPTSubscriptionVisionModel,'_open',self.transport(sent,always_invalid=True)), \
             patch.dict(os.environ,{'LHA_MODEL_FORMAT_ATTEMPTS':'2'}):
            with self.assertRaises(ModelAnswerUnavailable):
                unified.qualitative_select(ROOT,topic,candidates,reviews,directory,self.model())
        self.assertEqual(len(sent),2)
        self.assertFalse((directory/'decision.json').exists())
        self.assertFalse((directory/'call/format-recovery/selected.json').exists())

    def test_original_recovery_command_resumes_round_three_and_only_renders_round_four(self):
        batch,runtime=self.setup_loop(n=4);topic=batch['topics'][0];sent=[]
        def choose(topic,candidates,reviews,directory,scope):
            return unified.qualitative_select(self.repo,topic,candidates,reviews,directory,
                                              accounting.attach(self.model(),scope))
        runtime.choose=choose
        with patch.object(ChatGPTSubscriptionVisionModel,'_open',self.transport(sent)), \
             patch.dict(os.environ,{'LHA_MODEL_FORMAT_ATTEMPTS':'1'}):
            with self.assertRaises(ModelAnswerUnavailable):self.run_loop(batch,runtime)
        folder=self.output/'methods'/topic['id']/'pe-loop'
        save(folder/'settlement.json',{'status':'recovery_required','batch_sha256':load(self.output/'batch.json')['sha256']})
        self.assertEqual(load(folder/'progress.json')['round'],3)
        self.assertEqual(load(folder/'progress.json')['phase'],'select')
        before={p:sha(p) for p in folder.glob('rounds/*/*.json')}
        old_call=folder/'rounds/0003/selection/call'
        before.update({old_call/name:sha(old_call/name) for name in ('input.json','response.txt','returned.json')})
        prior=list(runtime.calls)
        import run_creative_benchmark as cli
        stdout=io.StringIO()
        with patch.object(sys,'argv',['run_creative_benchmark.py','recover-pe-loop','--output',str(self.output),
                 '--topic',topic['id'],'--reason','Repair selection citation response handling']), \
             patch('experiments.creative_benchmark.verify_batch',return_value=batch),contextlib.redirect_stdout(stdout):
            cli.main()
        self.assertEqual(json.loads(stdout.getvalue())['model_calls'],0)
        with patch.object(ChatGPTSubscriptionVisionModel,'_open',self.transport(sent)):
            result=self.run_loop(batch,runtime)
        self.assertEqual(result['status'],'ready')
        new=runtime.calls[len(prior):]
        self.assertEqual([row for row in new if row[0]=='render'],[('render',45)])
        self.assertEqual(len([row for row in new if row[0]=='review']),1)
        self.assertEqual(len([row for row in new if row[0]=='refine']),1)
        self.assertEqual(len(sent),4) # round 2, invalid 3, corrected 3, round 4
        self.assertTrue(all(sha(path)==digest for path,digest in before.items()))
        choice=load(folder/'rounds/0003/choice.json')['value'][1]
        self.assertEqual(choice['response_sha256'],sha(choice['response_call']['response_path']))


if __name__=='__main__':unittest.main()
