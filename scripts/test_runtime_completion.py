"""Production CLI -> HTTP/SSE parser -> tools -> four renders -> recovery/delivery.

Only external HTTP bytes and GPU inference are substituted. No Planner, decoder,
queue, accounting, image observation or delivery implementation is replaced.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from collections import deque
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from vlm.chatgpt_subscription import ChatGPTSubscriptionVisionModel
from planner_harness.common import load, save, sha
from planner_harness import PlannerHarness, accounting as accounting
from planner_harness.model_call import call_text
from planner_harness.model_answers import call_object
from planner_harness.delivery import verify_delivery
from test_subscription_stream_recovery import body
from test_loop_engineering import Renderer
from test_review_modes import action
import test_planner_harness as fixture
import run_server_pipeline as cli


class RecoveryCompletion(unittest.TestCase):
    setUp, tearDown = fixture.Tests.setUp, fixture.Tests.tearDown

    def transport(self, answers, sent):
        def receive(client, request, timeout):
            packet = json.loads(request.data)
            sent.append((client.role, packet))
            value = answers[client.role].popleft()
            if isinstance(value, BaseException):
                raise value
            text = value if isinstance(value, str) else json.dumps(value)
            response = io.BytesIO(body(text, '{"action":"generate","prompt":"MUST NOT EXECUTE"}')
                                  .replace(b'gpt-6.1-sol', packet['model'].encode()))
            response.status = 200
            response.headers = {'Content-Type': 'text/event-stream'}
            return response
        return receive

    def test_public_service_command_completes_four_rounds_after_empty_format_and_crash(self):
        worker = self.root / 'service'
        config = self.root / 'config.json'
        manifest = self.root / 'tasks.json'
        model = 'openai/gpt-6-luna'
        spec = {'factory':'vlm.chatgpt_subscription:ChatGPTSubscriptionVisionModel',
                'options':{'model':model, 'reasoning_effort':'high', 'relay_url':'http://127.0.0.1:18767'}}
        save(config, {'workflow':'creative_loop_v1','review':{'mode':'critic'},
             'credential_file':str(self.root / 'no-credentials'),
             'models':{'planner':spec, 'online_critic':spec},
             'renderer':{'backend':'bernini','generation':{},'seed':42}})
        save(manifest, [{'id':'same-task','source':str(self.source),'source_sha256':sha(self.source),
             'request':'Make the scene blue.','max_generations':4,
             'execution':{'mode':'live','resource_policy':{'max_generations':4},
                'continuation_policy':{'completion_policy':'fixed_generation_budget'},
                'renderer':{'backend':'bernini','seed':42,'generation':{}}}}])
        answers = {
            'planner':deque(['', 'I have not returned the requested action JSON.',
                {'action':'generate','input_video':'source','prompt':'First blue treatment.'},
                {'action':'observe','video':'v1','count':3},
                action('generate',input_video='v1',prompt='Second blue treatment.'),
                action('generate',input_video='source',prompt='Third blue treatment.'),
                action('generate',input_video='v1',prompt='Fourth blue treatment.'),
                action('finish',video='v2',message='The second candidate is preferred after review.')]),
            'online_critic':deque(['', '{"action":', {'action':'observe','video':'v1','count':2},
                *[action('review',summary='The supplied candidate shows a blue scene.',findings=[]) for _ in range(4)]])}
        sent, renders = [], []
        source = self.source
        class LocalRenderer(Renderer):
            def __init__(inner, *args, **kwargs):
                super().__init__(source)
                inner.calls = renders
        def command(*args):
            with contextlib.redirect_stdout(io.StringIO()):
                cli.main(['--service',str(worker),*args])
        original = PlannerHarness.operate
        def interrupt(h, operation, event):
            if operation['action'] == 'finish':
                raise KeyboardInterrupt('Crash after final answer saved, before delivery commit')
            return original(h, operation, event)
        with patch.object(ChatGPTSubscriptionVisionModel,'_open',self.transport(answers,sent)), \
             patch('server_runtime.renderers.ProcessRenderer',LocalRenderer), \
             patch('planner_harness.model_call.time.sleep'), \
             patch.object(socket.socket,'connect',side_effect=AssertionError('No external connection allowed')):
            command('init','--config',str(config))
            command('submit','--manifest',str(manifest))
            with patch.object(PlannerHarness,'operate',interrupt), self.assertRaises(KeyboardInterrupt):
                command('run','--once')
            run = worker / 'tasks/same-task/run'
            before = load(run / 'state.json')
            self.assertEqual(len(renders),4)
            self.assertEqual(len(before['submitted_generation_ids']),4)
            count = len(sent)
            command('run','--once')
            self.assertEqual(verify_delivery(run)['selected'],'v2')
            command('run','--once')
            self.assertEqual((len(renders),len(sent)),(4,count))
        state = load(run / 'state.json')
        self.assertEqual(state['submitted_generation_ids'],before['submitted_generation_ids'])
        self.assertEqual(state['online_clock'],before['online_clock'])
        self.assertTrue(all(row['status'] == 'ok' for row in state['events'] if row.get('event_id')))
        observations = [o for o in state['observations'] if o['video_id']=='v1']
        self.assertTrue(any(len(o['frames'])==3 for o in observations))
        self.assertEqual(load(run/'calls/event-0001/transport/returned.json')['attempt'],2)
        self.assertEqual(load(run/'calls/event-0001/transport/format-recovery/selected.json')['attempt'],1)
        self.assertEqual(len(state['reviews']),4)
        self.assertTrue(all(p['model']=='gpt-6-luna' for _,p in sent))
        # Only protocol repair packets contain bad replies; they never become
        # creative history or a maintenance event.
        for role, packet in sent:
            text=packet['input'][0]['content'][0]['text']
            if 'format_error' not in text:
                self.assertNotIn('JSONDecodeError',text)
        self.assertNotIn('MUST NOT EXECUTE',json.dumps(state))

    def test_eleven_empty_completions_recover_same_request_and_usage(self):
        sent=[]; answers={'planner':deque(['']*11+['{"ok":true}'])}
        model=ChatGPTSubscriptionVisionModel(model='openai/gpt-6-luna',relay_url='http://127.0.0.1:18767')
        call=self.root/'call'
        with patch.object(ChatGPTSubscriptionVisionModel,'_open',self.transport(answers,sent)):
            text=call_text(call,model,'s','u',[],retry_delay=0)
            self.assertEqual(text,'{"ok":true}')
            self.assertEqual(call_text(call,model,'s','u',[],retry_delay=0),text)
        self.assertEqual(len(sent),12)
        self.assertEqual(load(call/'returned.json')['attempt'],12)
        for n in range(1,12):
            self.assertEqual((call/f'attempts/{n:02d}/response.txt').read_text(),'')
            self.assertEqual(load(call/f'attempts/{n:02d}/result.json')['usage']['total_tokens'],12)
        self.assertEqual(len({json.dumps(p,sort_keys=True) for _,p in sent}),1)

    def test_saved_binding_is_used_for_original_and_format_recovery(self):
        call=self.root/'call'
        save(call/'input.json',{'system_prompt':'s','user_text':'u','images':[],
             'model':'openai/gpt-6.1-sol','reasoning_effort':'high'})
        model=ChatGPTSubscriptionVisionModel(model='openai/gpt-6-luna',relay_url='http://127.0.0.1:18767')
        sent=[];answers={'planner':deque(['non JSON','{"ok":true}'])}
        with patch.object(ChatGPTSubscriptionVisionModel,'_open',self.transport(answers,sent)):
            self.assertEqual(call_object(call,model,'new','new',[])[0],{'ok':True})
        self.assertEqual([p['model'] for _,p in sent],['gpt-6.1-sol','gpt-6.1-sol'])
        self.assertEqual(model.model,'openai/gpt-6-luna')

    def test_pe_enhancement_recovers_empty_and_invalid_prompt_without_restarting_round(self):
        from experiments.pe_loop import rewrite
        from planner_harness.video import Video
        source=Video(self.source,self.root/'pe-source').info
        model=ChatGPTSubscriptionVisionModel(model='openai/gpt-6-luna',relay_url='http://127.0.0.1:18767')
        sent=[];answers={'planner':deque(['', {'prompt':''}, {'prompt':'Render a coherent blue painted scene.'}])}
        with patch.object(ChatGPTSubscriptionVisionModel,'_open',self.transport(answers,sent)), \
             patch('planner_harness.model_call.time.sleep'):
            topic={'request':'Make the scene blue.','prompt_form':'short','source_info':source}
            result=rewrite(topic,self.root/'pe',model,[])
            self.assertEqual(result,'Render a coherent blue painted scene.')
            self.assertEqual(rewrite(topic,self.root/'pe',model,[]),result)
        self.assertEqual(len(sent),3)
        self.assertEqual(load(self.root/'pe/call/format-recovery/selected.json')['attempt'],1)

    def test_maintenance_recovers_response_and_activates_corrected_contribution_once(self):
        from test_loop_protocol_upgrade import IntegrationTests
        from planner_harness import maintenance, training_experience as tx
        run=IntegrationTests().run_record(self.root)
        state=load(run/'state.json')
        state['videos']={'v1':{'path':str(self.source),'sha256':sha(self.source)}}
        save(run/'state.json',state)
        library=tx.initialize(ROOT,self.root)
        profile=maintenance.stage_profile(ROOT,self.root,{'model_calls':3,'attempts':2})
        job=maintenance.enqueue(ROOT,self.root,run,split='train',topic='fixture',method='none',
            batch_sha256='fixture',maintenance_profile=profile,maintenance_snapshot=library)
        def model():
            return ChatGPTSubscriptionVisionModel(role='maintenance',model='openai/gpt-6-luna',
                                                  relay_url='http://127.0.0.1:18767')
        sent=[]; answers={'maintenance':deque(['', 'A response without the required action.',
            {'action':'contribute','text':'A continuous blue material coordinates the visible room.',
             'changes':[{'op':'create','id':'proposal-transport-fixture','title':'Blue construction',
                 'summary':'Use a continuous blue material.','text':'Use a continuous blue material to unify the room.'}]}])}
        with patch.object(ChatGPTSubscriptionVisionModel,'_open',self.transport(answers,sent)), \
             patch('planner_harness.model_call.time.sleep'):
            result=tx.maintain(ROOT,self.root,run,job,model_factory=model)
            self.assertEqual(result['status'],'activated',result)
            self.assertEqual(tx.maintain(ROOT,self.root,run,job,model_factory=model),result)
        self.assertEqual(len(sent),3)
        self.assertEqual(len(list((self.root/'training-experience/activations').glob('*.json'))),1)
        self.assertFalse((self.root/'maintenance/jobs'/job/'training-attempt-2').exists())

    def test_original_step_can_resume_after_format_retry_window(self):
        from planner_harness.model_answers import ModelAnswerUnavailable
        model=ChatGPTSubscriptionVisionModel(relay_url='http://127.0.0.1:18767')
        sent=[];answers={'planner':deque(['unusable text']*12+['{"ok":true}'])}
        call=self.root/'format-call'
        with patch.object(ChatGPTSubscriptionVisionModel,'_open',self.transport(answers,sent)):
            with self.assertRaises(ModelAnswerUnavailable):
                call_object(call,model,'s','u',[])
            digest=sha(call/'input.json')
            result,_=call_object(call,model,'s','u',[])
        self.assertEqual(result,{'ok':True})
        self.assertEqual(len(sent),13)
        self.assertEqual(sha(call/'input.json'),digest)

    def test_saved_actual_relay_streams_recover_final_without_network(self):
        from vlm.responses_stream import replay_answer
        root=ROOT/'out/planner-preexperience-021-022-25598-20261106'
        streams=list((root/'subscription-relay-audit').glob('*/*/stream.bin'))
        if not streams:
            self.skipTest('Local saved incident streams are not in this public checkout')
        checked=0
        class NoRequest:
            model='openai/gpt-6-luna';reasoning_effort='high'
            def predict_text(self,**kwargs):
                raise AssertionError('Saved usable final must not issue a request')
        for stream in streams:
            try: answer=replay_answer(stream)
            except ValueError: continue
            if not answer['text'].strip(): continue
            call=self.root/f'replay-{checked}'
            entry=call/'attempts/01'
            (entry/'client-audit').mkdir(parents=True)
            (entry/'client-audit/stream.bin').write_bytes(stream.read_bytes())
            (entry/'response.txt').write_text('')
            (call/'response.txt').write_text('')
            save(entry/'result.json',{'usage':{'total_tokens':17}})
            self.assertEqual(call_text(call,NoRequest(),'s','u',[],retry_delay=0),answer['text'])
            self.assertEqual((entry/'response.txt').read_text(),'')
            self.assertEqual(load(call/'returned.json')['usage'],{'total_tokens':17})
            checked+=1
        self.assertGreaterEqual(checked,1)


if __name__=='__main__': unittest.main()
