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
from planner_harness.maintenance_reading import retain, input_view
from planner_harness.common import page
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

    def test_equivalent_clamped_pages_preserve_all_unique_evidence(self):
        cache,history=[],[]
        for number in range(6):
            action={'action':'read','arguments':{'source':'run','id':str(number),'max_chars':12000}}
            retain(cache,history,action,page(str(number)*12000,max_chars=8000,split_long_lines=True),number+1)
        for number,size in enumerate((12000,15000,24000,26000),7):
            action={'action':'read','arguments':{'source':'run','id':'0','max_chars':size}}
            result=page('0'*12000,max_chars=8000,split_long_lines=True)
            retain(cache,history,action,result,number)
            self.assertEqual(result['already_read_at_step'],1)
            self.assertEqual(result['next_page']['arguments']['start_char'],result['next_char'])
        self.assertEqual(len(cache),6)
        self.assertGreater(sum(len(row['result']['text']) for row in cache),24000)
        self.assertEqual(len(history),10)

    def test_actual_call_context_precedes_long_system_manual(self):
        text=json.dumps({'system_prompt':'manual '*5000,'user_text':json.dumps({'task':'Actual user request'}),'images':[]})
        result=page(input_view(text),max_chars=8000,split_long_lines=True)
        self.assertIn('Actual user request',result['text'])
        self.assertEqual(json.loads(input_view(text))['system_prompt'],'manual '*5000)

    def test_final_step_accepts_findings_and_requests_contribution_for_a_read(self):
        with self.assertRaisesRegex(ValueError,'final maintenance step'):
            normalize({'read':{'source':'run','id':'state'}},final_step=True)
        self.assertEqual(normalize({'contribute':{'text':'Case findings','changes':[]}},final_step=True)['action'],'contribute')


class MaintenanceCompletion(unittest.TestCase):
    setUp = completion_tests.RecoveryCompletion.setUp
    tearDown = completion_tests.RecoveryCompletion.tearDown

    def run_maintenance(self, first, *, old_failures=False, invalid_first=False, final_read=False):
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
                      [first]+([{'read':{'source':'run','id':'state'}}] if final_read else [])+
                      [{'contribute':{'text':'No experience increment from this short fixture.','changes':[]}}])
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
        self.assertEqual(len(sent),3 if invalid_first or final_read else 2)
        final_input=json.loads(sent[-1]['input'][0]['content'][0]['text'])
        if final_read:final_input=json.loads(final_input['original_input'])
        self.assertEqual(final_input['maintenance_progress']['stage'],'submit')
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
        if final_read:
            self.assertEqual(load(calls/'0002/format-recovery/selected.json')['attempt'],1)

    def test_nested_skill_is_loaded_and_next_step_receives_its_text(self):
        self.run_maintenance({'skill':{'id':'lha-experience-analysis'}})

    def test_string_skill_is_loaded_and_next_step_receives_its_text(self):
        self.run_maintenance({'skill':'lha-experience-analysis'})

    def test_invalid_action_is_corrected_without_consuming_a_maintenance_step(self):
        self.run_maintenance({'skill':'lha-experience-analysis'},invalid_first=True)

    def test_two_failed_32_call_attempts_survive_maintenance_only_recovery(self):
        self.run_maintenance({'skill':'lha-experience-analysis'},old_failures=True)

    def test_last_step_read_is_corrected_to_the_models_own_contribution(self):
        self.run_maintenance({'skill':'lha-experience-analysis'},final_read=True)

    def test_recover_32_saved_steps_with_one_submission_and_no_repeated_read_calls(self):
        from planner_harness import maintenance, training_experience as tx
        from planner_harness import maintenance_actions
        run=protocol_tests.IntegrationTests().run_record(self.root)
        library=tx.initialize(ROOT,self.root)
        profile=maintenance.stage_profile(ROOT,self.root,{'model_calls':32,'attempts':1})
        job=maintenance.enqueue(ROOT,self.root,run,split='train',topic='fixture',method='none',
            batch_sha256='fixture',maintenance_profile=profile,maintenance_snapshot=library)
        folder=self.root/'maintenance/jobs'/job
        sent=[]
        def model():
            return ChatGPTSubscriptionVisionModel(role='maintenance',model='openai/gpt-6-luna',relay_url='http://127.0.0.1:18767')
        replies=deque([{'skill':'lha-experience-analysis'}]+[
            {'read':{'source':'reference','id':'docs/experience-authoring-standard.md','max_chars':12000+i*1000}}
            for i in range(31)])
        def receive(client,request,timeout):
            packet=json.loads(request.data);sent.append(packet)
            result=io.BytesIO(submission_body(json.dumps(replies.popleft()),packet['model']))
            result.status=200;result.headers={'Content-Type':'text/event-stream'}
            return result
        original=maintenance_actions.normalize
        # Reproduce the old contract: a read was allowed on all 32 steps.
        with patch.object(ChatGPTSubscriptionVisionModel,'_open',receive), \
             patch.object(maintenance_actions,'normalize',side_effect=lambda v,**kw:original(v,skills=kw.get('skills'))):
            result=tx.maintain(ROOT,self.root,run,job,model_factory=model)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(len(sent),32)
        before={p:sha(p) for p in (folder/'training-attempt-1/calls').rglob('*') if p.is_file()}
        before_run=sha(run/'state.json')
        replies.append({'contribute':{'text':'The retained source supports this prose-only finding.','changes':[]}})
        with patch.object(ChatGPTSubscriptionVisionModel,'_open',receive):
            result=tx.maintain(ROOT,self.root,run,job,model_factory=model)
        self.assertEqual(result['status'],'no_increment',result)
        self.assertEqual(len(sent),33)
        final=json.loads(sent[-1]['input'][0]['content'][0]['text'])
        self.assertEqual(final['maintenance_progress']['step'],32)
        self.assertEqual(len(final['operation_history']),31)
        self.assertEqual(len(final['retained_reading']),1)
        changed=[str(p.relative_to(folder)) for p,digest in before.items() if sha(p)!=digest]
        self.assertEqual(changed,[])
        self.assertEqual(sha(run/'state.json'),before_run)
        contribution=load(folder/'training-attempt-1/contribution.json')
        self.assertTrue(contribution['contribution_call']['path'].endswith('calls/0032/submission'))


if __name__=='__main__':
    unittest.main()
