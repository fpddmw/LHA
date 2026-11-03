"""API transport contract: original images, exact prompts, usage and durable calls."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
from vlm.openrouter import OpenRouterVisionModel, APIError, load_credentials


class Reply:
    ok = True
    status_code = 200
    reason = 'OK'
    def __init__(self, **overrides):
        self.body = {'id': 'test-response', 'model': 'openai/gpt-6.1-sol', 'provider': 'fixture',
            'usage': {'prompt_tokens': 12, 'completion_tokens': 7, 'total_tokens': 19, 'cost': 0.001},
            'choices': [{'message': {'content': '```json\n{"ok": true}\n```'}, 'finish_reason': 'stop'}]}
        self.body.update(overrides)
    def json(self): return self.body
    def __iter__(self): return iter((self.status_code, self.body))


class APITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-secret-never-record',
            'OPENROUTER_BASE_URL': 'https://openrouter.ai/api/v1', 'LHA_API_ENV_FILE': str(self.root/'absent')})
        self.env.start(); self.addCleanup(self.env.stop)
    def test_exact_multimodal_request_and_provider_default(self):
        image = self.root/'frame.png'; image.write_bytes(b'\x89PNG\r\n\x1a\nfixture')
        client = OpenRouterVisionModel()
        with patch('vlm.openrouter._post', return_value=Reply()) as post:
            result = client.predict_json(system_prompt='Only these instructions.', user_text='Inspect this.', image_paths=[str(image)])
        self.assertEqual(result, {'ok': True})
        body = post.call_args.kwargs['json']
        self.assertEqual(body['messages'][0], {'role':'system','content':'Only these instructions.'})
        self.assertEqual(body['messages'][1]['content'][0]['text'], 'Inspect this.')
        self.assertTrue(body['messages'][1]['content'][1]['image_url']['url'].startswith('data:image/png;base64,'))
        self.assertNotIn('max_tokens', body)
        self.assertEqual(body['reasoning'], {'effort':'high','exclude':True})
        self.assertEqual(client.last_usage['cost'], .001)
        self.assertEqual(client.last_finish_reason, 'stop')
        self.assertNotIn('test-secret', json.dumps(client.runtime_identity()) + json.dumps(client.last_client_audit))
    def test_explicit_token_limit_is_sent(self):
        client = OpenRouterVisionModel(output_limit_mode='hard')
        with patch('vlm.openrouter._post', return_value=Reply()) as post:
            client.predict_text(system_prompt='s',user_text='u',image_paths=[],max_new_tokens=123)
        self.assertEqual(post.call_args.kwargs['json']['max_tokens'],123)
        self.assertTrue(client.budget_capabilities()['hard_output_tokens'])
    def test_error_is_actionable_without_key(self):
        reply=Reply(error={'message':'bad key test-secret-never-record and sk-example-secret','code':401})
        reply.ok=False;reply.status_code=401
        with patch('vlm.openrouter._post',return_value=reply):
            with self.assertRaises(APIError) as raised:
                OpenRouterVisionModel().predict_text(system_prompt='s',user_text='u',image_paths=[])
        self.assertFalse(raised.exception.retryable)
        self.assertNotIn('test-secret',str(raised.exception))
        self.assertNotIn('sk-example',json.dumps(raised.exception.safe_diagnostic))
    def test_explicit_no_reasoning_overrides_default(self):
        client=OpenRouterVisionModel(model='configured/non-reasoning',reasoning_effort=None)
        with patch('vlm.openrouter._post',return_value=Reply()) as post:
            client.predict_text(system_prompt='s',user_text='u',image_paths=[])
        self.assertIsNone(client.reasoning_effort)
        self.assertNotIn('reasoning',post.call_args.kwargs['json'])
    def test_rate_limit_retry_classification(self):
        from planner_harness.model_call import transient
        self.assertTrue(transient(APIError(429,'Rate limit')))
        self.assertFalse(transient(APIError(402,'Insufficient balance')))
    def test_external_credentials_do_not_override_environment(self):
        path=self.root/'private.env';path.write_text('OPENROUTER_API_KEY=file-secret\nOPENROUTER_BASE_URL=https://example.invalid\n')
        load_credentials(path)
        self.assertEqual(os.environ['OPENROUTER_API_KEY'],'test-secret-never-record')
        self.assertEqual(os.environ['OPENROUTER_BASE_URL'],'https://openrouter.ai/api/v1')
    def test_external_credentials_can_configure_server_forwarding(self):
        path=self.root/'route.env';path.write_text('HTTPS_PROXY=http://127.0.0.1:17892\nNO_PROXY=localhost,127.0.0.1\n')
        with patch.dict(os.environ,{},clear=True):
            load_credentials(path)
            self.assertEqual(os.environ['HTTPS_PROXY'],'http://127.0.0.1:17892')
            self.assertEqual(os.environ['NO_PROXY'],'localhost,127.0.0.1')
    def test_independent_judges_share_openrouter_without_output_cap(self):
        from evaluation.creative import make_judge, judge_identity
        for slot,wire,effort in [('glm5.3flash','z-ai/glm-5.3-flash',None),
                                 ('sonnet-5.5high','anthropic/claude-sonnet-5.5','high')]:
            with self.subTest(slot=slot):
                judge=make_judge(slot)
                with patch('vlm.openrouter._post',return_value=Reply(model=wire)) as post:
                    judge.predict_text(system_prompt='s',user_text='u',image_paths=[],max_new_tokens=17)
                body=post.call_args.kwargs['json']
                self.assertEqual(judge.model,slot);self.assertEqual(body['model'],wire)
                self.assertEqual(judge_identity(slot)['provider'],'openrouter')
                self.assertEqual(judge.runtime_identity()['provider_model'],wire)
                self.assertEqual(judge.last_client_audit['requested_model'],wire)
                self.assertNotIn('max_tokens',body)
                self.assertEqual(body.get('reasoning'),{'effort':effort,'exclude':True} if effort else None)
    def test_api_is_default_without_cli(self):
        from vlm import resolve_vision_model
        with patch.dict(os.environ,{'LOW_HIGH_AGENT_VLM_BACKEND':'openrouter'}), patch('subprocess.Popen',side_effect=AssertionError('No CLI')):
            self.assertIsInstance(resolve_vision_model(),OpenRouterVisionModel)
    def test_durable_call_reuses_response_and_records_usage(self):
        from planner_harness.model_call import call_text
        from planner_harness.common import load
        client=OpenRouterVisionModel();directory=self.root/'call'
        with patch('vlm.openrouter._post',return_value=Reply()) as post:
            first=call_text(directory,client,'s','u',[])
            second=call_text(directory,client,'s','u',[])
        self.assertEqual(first,second);self.assertEqual(post.call_count,1)
        self.assertEqual(load(directory/'returned.json')['usage']['total_tokens'],19)
        for p in directory.rglob('*'):
            if p.is_file():self.assertNotIn('test-secret-never-record',p.read_text())
    def test_real_http_transport_sends_json_and_bearer_header(self):
        received=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                received.append((self.path,self.headers.get('Authorization'),json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                data=json.dumps(Reply().body).encode()
                self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        with HTTPServer(('127.0.0.1',0),Handler) as server:
            thread=threading.Thread(target=server.handle_request,daemon=True);thread.start()
            client=OpenRouterVisionModel(base_url=f'http://127.0.0.1:{server.server_port}/api/v1')
            answer=client.predict_json(system_prompt='Exact system',user_text='Unicode 检查',image_paths=[])
            thread.join(2)
        self.assertEqual(answer,{'ok':True})
        self.assertEqual(received[0][0],'/api/v1/chat/completions')
        self.assertEqual(received[0][1],'Bearer test-secret-never-record')
        self.assertEqual(received[0][2]['messages'][1]['content'][0]['text'],'Unicode 检查')
    def test_service_respects_distinct_configured_api_roles(self):
        from server_runtime.service import Service
        service=Service.__new__(Service);service.directory=self.root
        service.config={'workflow':'creative_loop_v1','planner':{'model':'configured/planner','reasoning_effort':'high'},
                        'critic':{'model':'configured/critic','reasoning_effort':None},'review':{'mode':'critic'}}
        with patch('subprocess.Popen',side_effect=AssertionError('No CLI')):
            planner=service.client('planner');critic=service.client('online_critic')
        self.assertEqual(planner.model,'configured/planner');self.assertEqual(critic.model,'configured/critic')
        self.assertIsNone(critic.reasoning_effort)
        # Factory options must also reach the frozen task and review identities.
        from planner_harness.common import load, sha
        from planner_harness.creative import role_settings
        config={'workflow':'creative_loop_v1','review':{'mode':'critic'},'models':{
            'planner':{'options':{'model':'configured/planner','reasoning_effort':'high'}},
            'online_critic':{'options':{'model':'configured/critic','reasoning_effort':None}}}}
        queue=Mock();directory=self.root/'service'
        with patch('planner_harness.accounting.install',return_value=self.root/'accounting'):
            service=Service(queue,directory,ROOT,config,renderer=object())
        frozen=load(directory/'critic-profile.json')
        self.assertEqual(frozen['model'],'configured/critic');self.assertIsNone(frozen['reasoning_effort'])
        source=self.root/'source.mp4';source.write_bytes(b'configuration fixture')
        service.submit({'id':'fixture','source':str(source),'source_sha256':sha(source),
            'request':'Edit the video','max_generations':5,'execution':{'renderer':{'backend':'bernini'}}})
        task=queue.enqueue.call_args.args[3]['task']
        self.assertEqual(role_settings(task['execution'],'online_critic'),{'model':'configured/critic','reasoning_effort':None})


if __name__=='__main__':unittest.main()
