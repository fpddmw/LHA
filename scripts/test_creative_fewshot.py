"""Offline coverage for activated experience and the three-arm topic gate."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from planner_harness.common import load, save, sha
from planner_harness.creative_knowledge import CreativeKnowledge
from planner_harness import PlannerHarness
from planner_harness.execution import collect
from critic_harness.one_shot import frozen_profile
from experiments import creative_fewshot as batch
from test_creative_loop import Scripted, action, review_fixture, CreativeTests
import test_planner_harness as legacy


class Judge:
    model = "glm5.3flash"
    reasoning_effort = None
    calls = 0
    def predict_text(self, **kwargs):
        type(self).calls += 1
        packet = json.loads(kwargs["user_text"])
        assert packet["candidate_id"] == "candidate"
        assert not packet["focus"] and not packet["extra_checks"]
        return json.dumps(review_fixture(kwargs["user_text"]))


class SonnetFixture(Judge):
    model = "sonnet-5.5high"
    reasoning_effort = "high"
    calls = 0


class ScopeTests(unittest.TestCase):
    def test_dual_provider_wire_contracts_are_separate(self):
        from evaluation.creative import ParateraJudge, SonnetJudge
        glm=ParateraJudge.build_payload('Rubric','Evidence',[])
        sonnet=SonnetJudge.build_payload('Rubric','Evidence',[])
        self.assertEqual(glm['model'],'GLM-5.3-Flash')
        self.assertEqual(glm['max_tokens'],16384)
        self.assertNotIn('output_config',glm)
        self.assertEqual(sonnet['model'],'claude-sonnet-5-5')
        self.assertEqual(sonnet['output_config'],{'effort':'high'})
        self.assertEqual(sonnet['thinking'],{'type':'adaptive'})
        self.assertEqual(sonnet['max_tokens'],7000)
    def test_activated_catalog_and_none_scope_survive_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            full = CreativeKnowledge(ROOT, experience_mode="full")
            none = CreativeKnowledge(ROOT, experience_mode="none")
            self.assertEqual(len(full.curated_catalog["entries"]), 14)
            self.assertEqual(full.manifest["entries"], none.manifest["entries"])
            self.assertEqual(full.manifest["domain_references"], none.manifest["domain_references"])
            for entry in full.curated_catalog["entries"] + full.curated_catalog["resources"]:
                full.resolve(entry["id"])
                with self.assertRaises(ValueError):
                    none.read(entry["id"])
                with self.assertRaises(ValueError):
                    none.read(entry["path"])
            for target in ["experience-map", "bernini-r-20261029", "experience", "LESSONS.md"]:
                with self.assertRaises((ValueError, KeyError)):
                    none.read(target)
            self.assertFalse(any('/staged/' in p or '/wiki/' in p for p in full.paths))
            self.assertTrue(none.search("watercolor"))
            self.assertFalse(any(x.get('id', '').startswith(('EX-', 'EV-')) for x in none.search('identity')['matches']))
            for mode, k in [('full', full), ('none', none)]:
                path = Path(tmp) / (mode + '.json'); k.freeze(path)
                restored = CreativeKnowledge(ROOT, path)
                self.assertEqual(restored.experience_mode, mode)
                self.assertEqual(set(restored.items), set(k.items))
                with self.assertRaises(ValueError):
                    CreativeKnowledge(ROOT, path, experience_mode='none' if mode == 'full' else 'full')

    def test_critic_identity_is_independent_of_experience_scope(self):
        before = frozen_profile()
        CreativeKnowledge(ROOT, experience_mode='full')
        CreativeKnowledge(ROOT, experience_mode='none')
        self.assertEqual(before, frozen_profile())


class LoopTests(unittest.TestCase):
    setUp, tearDown = legacy.Tests.setUp, legacy.Tests.tearDown
    respond = CreativeTests.respond

    def test_temporal_window_endpoints_require_every_intervening_frame(self):
        from critic_harness.one_shot import prepare_request,validate_report
        from planner_harness.video import Video
        info=Video(self.source,self.root/'info').info
        packet,_=prepare_request('Change color.','candidate',{'source':info,'candidate':info},self.root/'evidence',frozen_profile())
        visible=json.loads(packet['user_text']);report=review_fixture(packet['user_text'])
        dense=[e for e in visible['evidence'] if e['id'].startswith('candidate:dense-0:')]
        report['main_scores']['temporal_consistency']['evidence_refs']=[dense[0]['id'],dense[-1]['id']]
        validate_report(report,packet)
        broken=copy.deepcopy(packet);visible['evidence']=[e for e in visible['evidence'] if e['id']!=dense[2]['id']]
        broken['user_text']=json.dumps(visible)
        with self.assertRaises(ValueError):validate_report(report,broken)

    def test_portable_report_links_original_model_records(self):
        from planner_harness.creative_report import report
        import re
        self.h=PlannerHarness(self.root/'run',Scripted([action('generate',input_video='source',prompt='Blue.')]))
        self.h.start(self.source,'Blue.',workflow='creative_loop_v1',mode='loop',execution={'mode':'replay'})
        self.respond();self.h.model=Scripted([action('finish',video='v1',message='Delivery.',stop_reason='satisfied')]);self.h.resume()
        target=self.root/'view';target.mkdir()
        report(target,self.h.state,record_directory=self.h.output)
        text=(target/'report.html').read_text()
        self.assertIn('Model input',text);self.assertIn('Model response',text)
        for link in re.findall(r'(?:href|src)="([^"]+)"',text):
            self.assertTrue((target/link).exists(),link)

    def test_four_generations_paired_seeds_and_early_delivery_without_forms(self):
        for mode in ['full', 'none']:
            output = self.root / mode
            self.h = PlannerHarness(output, Scripted([action('generate', input_video='source', prompt='Blue.')]))
            self.h.start(self.source, 'Make it blue.', workflow='creative_loop_v1', mode='loop',
                execution={'mode':'replay','experience_mode':mode,'seed_sequence':{'start':42,'step':1}},max_generations=None,max_turns=None)
            for n in range(4):
                self.respond()
                operation = action('generate', input_video='source', prompt='Blue again.') if n < 3 else action('finish', video='v2', message='Selected delivery.', stop_reason='satisfied')
                self.h.model = Scripted([operation]); self.h.resume()
            state = self.h.state
            self.assertEqual(state['status'],'complete')
            self.assertEqual(state['final']['video'],'v2')
            seeds = [j['payload']['renderer']['seed'] for j in state['jobs'].values() if j['kind']=='generate']
            self.assertEqual(seeds,[42,43,44,45])
            self.assertFalse(state.get('requirements'))
            self.assertFalse(state['evaluations'])
            self.assertEqual(self.h.knowledge.experience_mode,mode)
            if mode=='none':self.assertNotIn('EX-design-conflict',json.dumps(self.h.knowledge.overview()))

    def test_failed_render_does_not_advance_seed(self):
        self.h = PlannerHarness(self.root/'run', Scripted([action('generate',input_video='source',prompt='Blue.')]))
        self.h.start(self.source,'Make it blue.',mode='loop',workflow='creative_loop_v1',
            execution={'mode':'replay','seed_sequence':{'start':42,'step':1}})
        job=self.h.state['jobs'][self.h.state['pending_tool']]
        save(self.h.output/'jobs'/job['id']/'response.json',{'request_sha256':job['sha256'],'mode':'replay','status':'failed','error':'Definite fixture failure'})
        self.h.model=Scripted([action('generate',input_video='source',prompt='Blue again.')]);self.h.resume()
        self.assertEqual([j['payload']['renderer']['seed'] for j in self.h.state['jobs'].values()],[42,42])


class BatchTests(unittest.TestCase):
    setUp, tearDown = legacy.Tests.setUp, legacy.Tests.tearDown

    def spec(self):
        from planner_harness.video import Video
        info=Video(self.source,self.root/'info').info
        return {'id':'first','source':str(self.source),'source_sha256':info['sha256'],
                'request':'Change the color.', 'source_info':info,'native_output':{'frames':5,'fps':info['fps']}}

    def receipt(self,topic,arm):
        from planner_harness.video import Video
        info=Video(self.source,self.root/'info').info
        record=self.root/'records'/topic['id']/arm;record.mkdir(parents=True,exist_ok=True)
        save(record/'trace.json',{'topic':topic['id'],'arm':arm,'software_fixture':True})
        result = {'arm':arm,'first':'v1','selected':'v1','record_directory':str(record),
                'videos':{'v1':{**info,'execution':{'generation_seconds':1}}}}
        result['binding']={'topic':topic['id'],'source':topic['source_sha256'],'request':batch.signature({'text':topic['request']}),'profile':'fixture'}
        result['completion_record']={'path':str(record/'trace.json'),'sha256':sha(record/'trace.json')}
        result['sha256']=batch.signature(result)
        return result

    def test_service_recovers_stable_planner_checkpoint_without_model_call(self):
        from server_runtime.service import Service
        service=object.__new__(Service)
        run=self.root/'stable';directory=self.root/'queue-result';directory.mkdir()
        save(run/'state.json',{'status':'waiting_tool','pending_event':None,'pending_tool':'job'})
        result=service.recover({'kind':'planner','payload':{'run':str(run)}},directory)
        self.assertEqual(result['state']['pending_tool'],'job')
        save(run/'state.json',{'status':'running','pending_event':'call'})
        self.assertIsNone(service.recover({'kind':'planner','payload':{'run':str(run)}},directory))

    def test_direct_receipt_recovery_does_not_render_or_change_signed_request(self):
        from experiments.recovery import recover_direct
        from server_runtime.queue import Queue
        topic=self.spec();output=self.root/'recovery';worker=output/'workers/0'
        save(output/'batch.json',{'topics':[topic]})
        folder=worker/'direct'/topic['id'];request=batch.direct_request(ROOT,topic,{'generation':batch.GENERATION,'seed_sequence':batch.SEEDS})
        save(folder/'request.json',request)
        q=Queue(worker/'queue.sqlite3',{'gpu':1,'llm':1,'cpu':1})
        identity=q.enqueue(topic['id']+'/direct','tool','gpu',{'request':str(folder/'request.json'),'request_sha256':request['sha256']})
        job=q.claim('gpu','fixture');q.finish(job,state='needs_review',error='Interrupted fixture')
        save(folder/'render-started.json',{'request_sha256':request['sha256']})
        receipt=output/'recovered.json'
        save(receipt,{'request_sha256':request['sha256'],'mode':'live','status':'complete','payload':{'video':topic['source_info']}})
        result=recover_direct(output,0,topic['id'],'Recovered original response',receipt=receipt)
        self.assertEqual(result['action'],'import_complete_receipt')
        self.assertEqual(q.rows()[0]['state'],'queued')
        self.assertEqual(load(folder/'request.json'),request)
        self.assertTrue((folder/'render-started.json').exists())

    def test_direct_is_exact_and_conditions_are_paired(self):
        topic=self.spec();manifest={'generation':batch.GENERATION,'seed_sequence':batch.SEEDS}
        direct=batch.direct_request(ROOT,topic,manifest)
        self.assertEqual(direct['payload']['prompt'],topic['request'])
        for arm in ['full','none']:
            task=batch.task_spec(topic,arm,manifest,Path('/frozen.json'))
            self.assertEqual(task['execution']['renderer'],direct['payload']['renderer'])
            self.assertIsNone(task['max_generations']);self.assertIsNone(task['max_turns'])
            self.assertNotIn('rsi',task)

    def test_topic_gate_resume_and_judge_hash_reuse(self):
        first=self.spec();second={**first,'id':'second','request':'Change the color differently.'}
        output=self.root/'batch';save(output/'profile.json',{'fixture':True});save(output/'batch.json',{'fixture':True})
        calls=[];Judge.calls=0;SonnetFixture.calls=0
        def execute(topic,arm):
            if topic['id']=='second':self.assertTrue((output/'topics/first/archive-manifest.json').exists())
            calls.append((topic['id'],arm));return self.receipt(topic,arm)
        with patch.object(batch,'verify_batch',return_value={'topics':[first,second],'profile_sha256':'fixture'}):
            result=batch.advance(ROOT,output,execute_arm=execute,judges={'glm5.3flash':Judge(),'sonnet-5.5high':SonnetFixture()})
            self.assertEqual(result['status'],'complete');self.assertEqual(len(calls),6)
            self.assertEqual(SonnetFixture.calls,2)
            self.assertEqual(Judge.calls,2) # same source/output/request scores reused across all positions
            batch.advance(ROOT,output,execute_arm=lambda *a:self.fail('must reuse archive'),judges={'glm5.3flash':Judge(),'sonnet-5.5high':SonnetFixture()})
            self.assertEqual(Judge.calls,2)
            self.assertEqual(set(result['comparisons']),set(batch.JUDGES))
            artifact=output/'topics/first/archive/videos/direct/v1.mp4'
            artifact.write_bytes(b'changed')
            with self.assertRaises(ValueError):batch.advance(ROOT,output,execute_arm=execute,judges={'glm5.3flash':Judge(),'sonnet-5.5high':SonnetFixture()})

    def test_judge_failure_does_not_admit_next_topic(self):
        first=self.spec();second={**first,'id':'second'};output=self.root/'blocked';calls=[]
        def execute(topic,arm):calls.append(topic['id']);return self.receipt(topic,arm)
        with patch.object(batch,'verify_batch',return_value={'topics':[first,second],'profile_sha256':'fixture'}),patch.object(batch,'cache_judgment',side_effect=RuntimeError('fixture judge failure')):
            with self.assertRaises(RuntimeError):batch.advance(ROOT,output,execute_arm=execute)
        self.assertEqual(calls,['first']*3)
        self.assertFalse((output/'topics/second').exists())

    def test_blocked_loop_does_not_advance(self):
        first=self.spec();second={**first,'id':'second'};calls=[]
        def execute(topic,arm):
            calls.append((topic['id'],arm))
            if arm=='full':raise RuntimeError('delivery_blocked')
            return self.receipt(topic,arm)
        with patch.object(batch,'verify_batch',return_value={'topics':[first,second],'profile_sha256':'fixture'}):
            with self.assertRaises(RuntimeError):batch.advance(ROOT,self.root/'blocked-loop',execute_arm=execute)
        self.assertEqual(calls,[('first','direct'),('first','full')])

    def test_second_judge_failure_preserves_first_and_blocks_next_topic(self):
        first=self.spec();second={**first,'id':'second'};output=self.root/'one-judge-blocked';calls=[]
        original=batch.cache_judgment
        def execute(topic,arm):calls.append(topic['id']);return self.receipt(topic,arm)
        def judge(*args,**kwargs):
            if kwargs['name']=='sonnet-5.5high':raise RuntimeError('Sonnet fixture failure')
            return original(*args,**kwargs)
        with patch.object(batch,'verify_batch',return_value={'topics':[first,second],'profile_sha256':'fixture'}),patch.object(batch,'cache_judgment',side_effect=judge):
            with self.assertRaises(RuntimeError):batch.advance(ROOT,output,execute_arm=execute,judges={'glm5.3flash':Judge(),'sonnet-5.5high':SonnetFixture()})
        self.assertEqual(calls,['first']*3)
        self.assertEqual(len(list((output/'final-judge').glob('*/judgment.json'))),1)
        self.assertFalse((output/'topics/first/archive-manifest.json').exists())

    def test_wrong_topic_receipt_is_rejected(self):
        topic=self.spec();result=self.receipt(topic,'full')
        with self.assertRaises(ValueError):batch.verify_arm({**topic,'request':'Another task'},'full',result,'fixture')


if __name__=='__main__':unittest.main()
