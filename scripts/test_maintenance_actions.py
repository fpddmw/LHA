"""Captured maintenance spellings, correction, and maintenance-only recovery."""
import io
import contextlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from collections import deque
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from planner_harness.common import load, save, sha
from planner_harness.maintenance_actions import normalize, calls_directory, INSTRUCTION
from vlm.chatgpt_subscription import ChatGPTSubscriptionVisionModel
from test_subscription_submission import submission_body
import test_loop_protocol_upgrade as protocol_tests
import test_runtime_completion as completion_tests


class ActionForms(unittest.TestCase):
    def test_both_captured_skill_spellings_have_the_same_execution(self):
        expected={'action':'skill','arguments':{'id':'lha-experience-analysis'}}
        for raw in ('{"skill":{"id":"lha-experience-analysis"}}',
                    '{"skill":"lha-experience-analysis"}',
                    '{"action":"skill","id":"lha-experience-analysis"}'):
            self.assertEqual(normalize(json.loads(raw)),expected)

    def test_missing_unknown_and_incomplete_operations_require_correction(self):
        for value in ({}, {'answer':'ok'}, {'action':'not_a_tool'},
                      {'action':'skill'}, {'read':{'id':'state'}},
                      {'skill':{'id':'x','unsupported':True}}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize(value)

    def test_valid_legacy_progress_keeps_its_original_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            save(folder/'calls/0001/input.json',{'user_text':json.dumps({'skills':[]})})
            self.assertEqual(calls_directory(folder),folder/'calls')
            self.assertEqual(calls_directory(folder),folder/'calls')


class MaintenanceCompletion(unittest.TestCase):
    setUp = completion_tests.RecoveryCompletion.setUp
    tearDown = completion_tests.RecoveryCompletion.tearDown

    def run_maintenance(self, first, *, old_failures=False, invalid_first=False):
        from planner_harness import maintenance, training_experience as tx
        run=protocol_tests.IntegrationTests().run_record(self.root)
        library=tx.initialize(ROOT,self.root)
        state=load(run/'state.json')
        state.update(status='complete', final={'outcome':'selected_video','video':'v1'},
                     videos={f'v{i}':{'path':str(self.source),'sha256':sha(self.source)} for i in range(1,5)})
        state['config']['execution'].update(experience_condition='pre-experience',
            experience_snapshot_sha256=library['snapshot_sha256'])
        save(run/'knowledge-snapshot.json',load(library['snapshot']))
        save(run/'state.json',state)
        before_run=sha(run/'state.json'); before_video=sha(self.source)
        profile=maintenance.stage_profile(ROOT,self.root,{'model_calls':2,'attempts':2})
        job=maintenance.enqueue(ROOT,self.root,run,split='train',topic='fixture',method='pre-experience',
            batch_sha256='fixture',maintenance_profile=profile,maintenance_snapshot=library)
        folder=self.root/'maintenance/jobs'/job
        old={}
        if old_failures:
            failure={'status':'failed','error_type':'RuntimeError','reason':'Maintenance call allowance exhausted'}
            save(folder/'training-maintenance.json',failure)
            for number in (1,2):
                attempt=folder/f'training-attempt-{number}'
                save(attempt/'failure.json',failure)
                for index in range(32):
                    call=attempt/'calls'/f'{index+1:04d}'
                    save(call/'input.json',{'user_text':json.dumps({'current_result':{'error':'Choose an available maintenance action'},'loaded_skills':{}})})
                    (call/'response.txt').write_text(json.dumps(first))
                old.update({p:sha(p) for p in attempt.rglob('*') if p.is_file()})
        replies=deque(([{'answer':'A response with no operation'}] if invalid_first else [])+
                      [first, {'contribute':{'text':'No experience increment from this short fixture.','changes':[]}}])
        sent=[]
        def receive(client,request,timeout):
            packet=json.loads(request.data);sent.append(packet)
            self.assertIn(INSTRUCTION,packet['instructions'])
            result=io.BytesIO(submission_body(json.dumps(replies.popleft()),packet['model']))
            result.status=200;result.headers={'Content-Type':'text/event-stream'}
            return result
        def model():
            return ChatGPTSubscriptionVisionModel(role='maintenance',model='openai/gpt-6-luna',relay_url='http://127.0.0.1:18767')
        with patch.object(ChatGPTSubscriptionVisionModel,'_open',receive):
            if old_failures:
                import run_creative_benchmark as cli
                topic={'id':'fixture','split':'train','methods':['pre-experience']}
                batch={'arms':['pre-experience'],'topics':[topic],'sha256':'fixture'}
                save(self.root/'topics/fixture/pre-experience.json',{'record_directory':str(run)})
                stdout=io.StringIO()
                with patch('experiments.creative_benchmark.verify_batch',return_value=batch), \
                     patch('experiments.unified_benchmark.maintenance_model',side_effect=lambda _:model()), \
                     patch.object(sys,'argv',['run_creative_benchmark.py','recover-maintenance',
                         '--output',str(self.root),'--topic','fixture']), contextlib.redirect_stdout(stdout):
                    cli.main()
                result=json.loads(stdout.getvalue())
            else:
                result=tx.maintain(ROOT,self.root,run,job,model_factory=model)
            self.assertEqual(result['status'],'no_increment',result)
            self.assertEqual(tx.maintain(ROOT,self.root,run,job,model_factory=model)['status'],result['status'])
        self.assertEqual(len(sent),3 if invalid_first else 2)
        final_input=json.loads(sent[-1]['input'][0]['content'][0]['text'])
        self.assertIn('lha-experience-analysis',final_input['loaded_skills'])
        self.assertNotIn('error',final_input['current_result'])
        self.assertEqual(sha(run/'state.json'),before_run)
        self.assertEqual(sha(self.source),before_video)
        self.assertTrue(all(sha(p)==digest for p,digest in old.items()))
        calls=calls_directory(folder/'training-attempt-1')
        self.assertEqual(calls.name,'calls-v2' if old_failures else 'calls')
        self.assertFalse((calls/'0003').exists())
        if invalid_first:
            self.assertEqual(load(calls/'0001/format-recovery/selected.json')['attempt'],1)

    def test_nested_skill_is_loaded_and_next_step_receives_its_text(self):
        self.run_maintenance({'skill':{'id':'lha-experience-analysis'}})

    def test_string_skill_is_loaded_and_next_step_receives_its_text(self):
        self.run_maintenance({'skill':'lha-experience-analysis'})

    def test_invalid_action_is_corrected_without_consuming_a_maintenance_step(self):
        self.run_maintenance({'skill':'lha-experience-analysis'},invalid_first=True)

    def test_two_failed_32_call_attempts_survive_maintenance_only_recovery(self):
        self.run_maintenance({'skill':'lha-experience-analysis'},old_failures=True)


if __name__=='__main__':
    unittest.main()
