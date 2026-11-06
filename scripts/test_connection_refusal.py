"""Local refusal accounting and original-command Planner/Critic recovery; offline."""
import contextlib
import copy
import errno
import io
import json
import os
from pathlib import Path
import socket
import sys
import unittest
import urllib.error
from collections import deque
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from planner_harness import accounting as a
from planner_harness.common import load,save,sha
from planner_harness.connection_recovery import refused_before_request
from planner_harness.model_call import call_text,ModelTransportError
from planner_harness.resumption import reconcile_accounting
from planner_harness.delivery import verify_delivery
from vlm.chatgpt_subscription import ChatGPTSubscriptionVisionModel
from test_subscription_submission import submission_body
from test_loop_engineering import Renderer
from test_review_modes import action
import test_runtime_completion as fixtures
import run_server_pipeline as cli


def refusal():return urllib.error.URLError(ConnectionRefusedError(errno.ECONNREFUSED,'Connection refused'))


class ConnectionRecovery(unittest.TestCase):
    setUp=fixtures.RecoveryCompletion.setUp
    tearDown=fixtures.RecoveryCompletion.tearDown

    def model(self):
        return ChatGPTSubscriptionVisionModel(model='openai/gpt-6-luna',relay_url='http://127.0.0.1:18767')

    def test_new_refusal_is_not_submitted_and_releases_only_its_reservation(self):
        call=self.root/'call'
        with patch.object(ChatGPTSubscriptionVisionModel,'_open',side_effect=refusal()):
            with self.assertRaises(ModelTransportError):call_text(call,self.model(),'s','u',[],attempts=1,retry_delay=0)
        failure=load(call/'attempts/01/failed.json')
        self.assertTrue(failure['retryable'])
        self.assertEqual(failure['client_execution']['outcome'],'not_submitted')
        self.assertFalse((call/'attempts/01/unknown.json').exists())
        root=next(self.root.rglob('ledger.json')).parent
        record=next(iter(a.load_ledger(root)['operations'].values()))
        self.assertEqual((record['status'],record['charged_tokens'],record['settled_amount']),('not_submitted',0,'0'))
        self.assertEqual(load(record['completion']['path'])['error_type'],'ExternalNotSubmitted')

    def test_reset_http_error_and_partial_stream_are_not_connection_refusals(self):
        valid={'backend':'chatgpt_subscription','endpoint':'http://127.0.0.1:18767/responses',
               'stage':'connect','finished_unix':1,'received_bytes':0,'event_count':0,
               'error':{'type':'URLError','errno':None,'message':'<urlopen error [Errno 111] Connection refused>'}}
        self.assertTrue(refused_before_request(valid))
        for change in ({'http_status':502},{'response_id':'resp_1'},{'received_bytes':1},
                       {'stage':'read_stream'},{'endpoint':'https://remote.example/responses'},
                       {'error':{'type':'ConnectionResetError','errno':104,'message':'Connection reset by peer'}}):
            self.assertFalse(refused_before_request({**valid,**change}))
        with patch.object(ChatGPTSubscriptionVisionModel,'_open',side_effect=ConnectionResetError(104,'Connection reset by peer')):
            with self.assertRaises(a.ExternalExecutionUnknown):
                self.model().predict_text(system_prompt='s',user_text='u',image_paths=[])

    def resume_service(self,role):
        worker=self.root/'service';config=self.root/'config.json';manifest=self.root/'tasks.json'
        n=2 if role=='online_critic' else 1
        spec={'factory':'vlm.chatgpt_subscription:ChatGPTSubscriptionVisionModel','options':{
            'model':'openai/gpt-6-luna','reasoning_effort':'high','relay_url':'http://127.0.0.1:18767'}}
        save(config,{'workflow':'creative_loop_v1','review':{'mode':'critic'},
             'models':{'planner':spec,'online_critic':spec},
             'renderer':{'backend':'bernini','generation':{},'seed':42}})
        save(manifest,[{'id':'same-task','source':str(self.source),'source_sha256':sha(self.source),
             'request':'Make the scene blue.','max_generations':n,'execution':{'mode':'live',
             'resource_policy':{'max_generations':n},'continuation_policy':{'completion_policy':'fixed_generation_budget'},
             'renderer':{'backend':'bernini','seed':42,'generation':{}}}}])
        answers={'planner':deque([*[action('generate',input_video='source',prompt=f'Blue treatment {i}.') for i in range(n)],
                                  action('finish',video=f'v{n}',message='Choose the reviewed blue candidate.')]),
                 'online_critic':deque([action('review',summary='The candidate shows a blue scene.',findings=[]) for _ in range(n)])}
        sent=[];renders=[];closed=True;success={'planner':0,'online_critic':0}
        def receive(client,request,timeout):
            packet=json.loads(request.data)
            unavailable=closed and client.role==role and (role=='planner' or success['online_critic']==1)
            sent.append((client.role,packet,unavailable))
            if unavailable:raise refusal()
            success[client.role]+=1
            response=io.BytesIO(submission_body(json.dumps(answers[client.role].popleft()),packet['model']))
            response.status=200;response.headers={'Content-Type':'text/event-stream'}
            return response
        source=self.source
        class LocalRenderer(Renderer):
            def __init__(inner,*args,**kwargs):super().__init__(source);inner.calls=renders
        def command(*args):
            with contextlib.redirect_stdout(io.StringIO()):cli.main(['--service',str(worker),*args])
        with patch.object(ChatGPTSubscriptionVisionModel,'_open',receive), \
             patch('server_runtime.renderers.ProcessRenderer',LocalRenderer), \
             patch('planner_harness.model_call.time.sleep'), \
             patch.dict(os.environ,{'LHA_MODEL_TRANSPORT_ATTEMPTS':'12'}), \
             patch.object(socket.socket,'connect',side_effect=AssertionError('No external network')):
            command('init','--config',str(config));command('submit','--manifest',str(manifest))
            # Reproduce the historical adapter's misclassification of URLError.
            with patch('vlm.chatgpt_subscription.connection_refused',return_value=False):
                try:command('run','--once')
                except SystemExit as exc:self.assertEqual(exc.code,2)
            run=worker/'tasks/same-task/run';state=load(run/'state.json')
            self.assertEqual(len(renders),2 if role=='online_critic' else 0)
            failures=[p for p in run.rglob('client-audit/summary.json') if refused_before_request(load(p))]
            self.assertEqual(len(failures),12)
            old={p:sha(p) for audit in failures for p in (audit,audit.with_name('stream.bin'),audit.parent.parent/'unknown.json')}
            root=Path(load(failures[0].parent.parent/'unknown.json')['scope']['root'])
            ledger=a.load_ledger(root);keys=[str(p.parent.parent.resolve()) for p in failures]
            self.assertTrue(all(ledger['operations'][key]['status']=='failed_unknown_cost' for key in keys))
            originals={p:sha(p) for p in (run/'jobs').glob('*/response.json') if load(p).get('status')=='complete'}
            input_path=failures[0].parent.parent.parent.parent/'input.json';input_hash=sha(input_path)
            clock=copy.deepcopy(state['online_clock']);submitted=list(state.get('submitted_generation_ids',[]))
            closed=False
            command('run','--once')
            self.assertEqual(verify_delivery(run)['selected'],f'v{n}')
            self.assertEqual(len(renders),n)
            self.assertTrue(all(sha(p)==digest for p,digest in old.items()))
            self.assertTrue(all(sha(p)==digest for p,digest in originals.items()))
            self.assertEqual(sha(input_path),input_hash)
            self.assertEqual(load(run/'state.json')['online_clock'],clock)
            now=a.load_ledger(root)
            self.assertTrue(all(now['operations'][key]['status']=='not_submitted' for key in keys))
            self.assertTrue(all(now['operations'][key]['charged_tokens']==0 for key in keys))
            self.assertTrue(all(now['operations'][key]['settled_amount']=='0' for key in keys))
            self.assertTrue(all(now['operations'][key]['completion']==ledger['operations'][key]['completion'] for key in keys))
            if role=='online_critic':self.assertEqual(load(run/'state.json')['submitted_generation_ids'],submitted)
            count=len(sent);command('run','--once');self.assertEqual(len(sent),count)
            self.assertEqual(reconcile_accounting(root),[])

    def test_second_critic_resumes_with_two_videos_unchanged(self):self.resume_service('online_critic')

    def test_first_planner_resumes_the_same_input_after_twelve_refusals(self):self.resume_service('planner')


if __name__=='__main__':unittest.main()
