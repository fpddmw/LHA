"""Cross-layer final-review regression, scripted providers and CPU fixture media only."""
import copy,json,threading,time,unittest,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import test_unified_results as base
import test_creative_loop as loop
from experiments import unified_benchmark as u,results
from planner_harness import PlannerHarness,accounting as a
from planner_harness.common import load,save,sha
from planner_harness.execution import signature,immutable


class Remediation(base.Fixture):
    def test_deadline_delivery_crosses_harness_verifier_method_registry_and_view(self):
        rows=copy.deepcopy(self.rows);rows[0]['split']='test';save(self.repo/'benchmark_data/benchmark.json',rows)
        batch=self.prepare(methods=['none'],best_of_n=None,splits=['test'],prompt_forms=['short'])
        batch=load(self.output/'batch.json');topic=batch['topics'][0]
        self.h=PlannerHarness(self.root/'run',loop.Scripted([loop.action('generate',input_video='source',prompt='Make it blue.')]))
        self.h.start(self.source,topic['request'],mode='loop',workflow='creative_loop_v1',execution={'mode':'replay','experience_mode':'none','renderer':{'seed':42},'seed_sequence':{'start':42,'step':1}})
        loop.CreativeTests.respond(self)
        state=load(self.h.output/'state.json');self.assertTrue(state['deadline_selection']['selected'])
        bad=copy.deepcopy(state);bad.update(status='budget_exhausted',final={'outcome':'deadline_delivery','planner_confirmed':False,'stop_reason':'deadline','selection':bad['deadline_selection']})
        save(self.root/'bad/state.json',bad)
        from planner_harness.delivery import verify_settlement
        with self.assertRaisesRegex(__import__('planner_harness.integrity',fromlist=['IntegrityError']).IntegrityError,'persisted freeze'):verify_settlement(self.root/'bad')
        with patch('time.time',return_value=state['online_clock']['deadline_unix']+1):self.h.resume()
        settled=verify_settlement(self.h.output)
        self.assertEqual(settled['outcome'],'deadline_delivery');self.assertFalse(settled['planner_confirmed'])
        state=load(self.h.output/'state.json');videos={k:v for k,v in state['videos'].items() if k!='source'}
        body={'arm':'none',**settled,'first':next(iter(videos)),'videos':videos,'record_directory':str(self.h.output),
            'binding':{'topic':topic['id'],'source':topic['source_sha256'],'request':signature({'text':topic['request']}),'profile':batch['profile_sha256']},
            'completion_record':{'path':str(self.h.output/'state.json'),'sha256':sha(self.h.output/'state.json')},'delivery_review':None}
        immutable(self.output/'topics'/topic['id']/'none.json',{**body,'sha256':signature(body)})
        a.install(self.output/'accounting')
        answer=u.execute_method(self.repo,self.output,topic,'none',batch,object())
        self.assertEqual(answer['delivery_kind'],'deadline_delivery')
        entry=results.find(self.registry,topic['sample_id'],'short','none',42)
        self.assertFalse(entry['evidence']['planner_confirmed']);self.assertEqual(entry['evidence']['actual_generations'],1)
        row=next(r for r in results.report(self.repo,self.registry)['results'] if r['method']=='none')
        self.assertEqual(row['video_sha256'],videos[settled['selected']]['sha256']);self.assertEqual(row['status'],'ready')
        positions=results.prepare_evaluation(self.repo,self.registry,evaluation_id='deadline')['positions']
        self.assertTrue(any(p['method']=='none' and p['position']=='final' and p['video_sha256']==row['video_sha256'] for p in positions))
        self.assertIn(['direct-best-of-n','none_final'],results.comparison_pairs())

    def test_partial_best_n_registers_unknown_dimensions_and_reused_compute(self):
        batch=self.prepare(methods=['direct-best-of-n'],best_of_n=3,splits=['train'],prompt_forms=['short'])
        batch=load(self.output/'batch.json');topic=batch['topics'][0]
        results.import_video(self.repo,self.registry,self.row())
        from planner_harness.video import Video
        from planner_harness.resources import ResourceExhausted
        outer=self
        class Runtime:
            def render(self,topic,method,prompt,seed,number,scope):
                if number==2:raise ResourceExhausted('fixture deadline')
                receipt=outer.root/'render.json';save(receipt,{'status':'complete'})
                return a.invoke(scope,'render-two','render','render:bernini',lambda:{'video':Video(outer.source,outer.root/'info').info,'response':str(receipt),'seed':seed})
            def review(self,topic,candidate,directory,scope):
                return {'report':{'summary':'The requested scene is visible.','findings':[]}}
            def choose(self,topic,candidates,reviews,directory,scope):
                return 1,{'policy':u.SELECTOR,'selected_index':1,'reason':'The second candidate shows the requested transformation more clearly.','model_called':True}
        a.install(self.output/'accounting')
        answer=u.execute_method(self.repo,self.output,topic,'direct-best-of-n',batch,Runtime())
        self.assertTrue(answer['partial'])
        entry=results.find(self.registry,'001','short','direct-best-of-n',42)
        selection=entry['evidence']['selection']
        self.assertEqual((selection['requested_n'],selection['actual_submitted'],selection['reused'],selection['effective_generation_count'],selection['completed']),(3,1,1,2,2))
        self.assertEqual(selection['selected_index'],1)
        self.assertEqual(selection['policy'],u.SELECTOR)
        view=results.report(self.repo,self.registry);self.assertTrue(any(r['method']=='direct-best-of-n' and r['status']=='ready' for r in view['results']))

    def test_best_n_known_failed_attempt_keeps_earlier_completed_candidate(self):
        self.prepare(methods=['direct-best-of-n'],best_of_n=3,splits=['train'],prompt_forms=['short'])
        batch=load(self.output/'batch.json');topic=batch['topics'][0]
        results.import_video(self.repo,self.registry,self.row());a.install(self.output/'accounting')
        class Runtime:
            def review(inner,*args):return None
            def render(inner,topic,method,prompt,seed,number,scope):
                def failure():raise RuntimeError('Known fixture execution failure; not a time stop')
                return a.invoke(scope,'definite-render-failure','render','render:bernini',failure)
        answer=u.execute_method(self.repo,self.output,topic,'direct-best-of-n',batch,Runtime())
        self.assertTrue(answer['partial'])
        entry=results.find(self.registry,'001','short','direct-best-of-n',42);selection=entry['evidence']['selection']
        self.assertEqual(selection['stop'],'RuntimeError');self.assertEqual(selection['completed'],1)
        self.assertEqual(selection['effective_generation_count'],2);self.assertEqual(selection['selected_index'],0)

    def test_model_unknown_releases_idle_gpu_for_next_topic_same_ledger(self):
        from server_runtime.service import Service
        from server_runtime.queue import Queue
        from server_runtime.engine import Engine
        from planner_harness.video import Video
        release=threading.Event();self.addCleanup(release.set)
        budget={'version':a.VERSION,'mode':'offline','max_call_seconds':.03}
        ar=a.install(self.output/'accounting',budget);binding=a.scope(ar,'original','full')
        directory=self.output/'worker'
        closed=[]
        class Renderer:
            def initialize(self):pass
            def close(self):closed.append(True)
            def __call__(inner,request,folder):return {'video':Video(self.source,self.root/'info').info,'execution':{}}
        q=Queue(directory/'queue.sqlite3',{'gpu':1,'llm':1,'cpu':1})
        service=Service(q,directory,ROOT,{'budget':budget,'accounting_root':str(ar)},renderer=Renderer())
        with self.assertRaises(a.ExternalExecutionUnknown):a.invoke(binding,'unknown-model','model','model:fixture',lambda:release.wait(4),owner=str(directory.resolve()))
        self.assertTrue(service.resources_unknown());self.assertFalse(service.gpu_unknown());service.ensure_ready()
        other=a.scope(ar,'next','full');body={'id':'next','kind':'generate','mode':'live','accounting_scope':other,'payload':{'input':{},'prompt':'Blue','renderer':{'backend':'fixture'}}}
        request={**body,'sha256':signature(body)};path=directory/'next/request.json';save(path,request)
        self.assertFalse(service.blocks_dispatch({'payload':{'request':str(path)}}))
        q.enqueue('next','tool','gpu',{'request':str(path),'request_sha256':request['sha256']})
        Engine(q,directory,service,service.expand,interval=.01).run(once=True)
        self.assertEqual(load(path.with_name('response.json'))['status'],'complete')
        self.assertEqual(a.operation(binding,'unknown-model')['status'],'in_flight_unknown')
        u.Runtime.close(type('Worker',(),{'service':service})())
        self.assertTrue(closed)
        release.set()

    def test_atomic_dynamic_claims_and_disjoint_shards(self):
        from experiments.device_scheduler import Claims,devices,shard_topics
        topics=[{'id':str(i)} for i in range(20)];claimed=[];guard=threading.Lock()
        def work(owner):
            queue=Claims(self.root/'queue.db',topics,'frozen-plan',owner)
            while True:
                topic=queue.next()
                if topic is None:return
                with guard:claimed.append(topic['id'])
                queue.finish(topic['id'],'settled')
        workers=[threading.Thread(target=work,args=(str(i),)) for i in range(3)]
        for t in workers:t.start()
        for t in workers:t.join()
        self.assertEqual(len(claimed),20);self.assertEqual(len(set(claimed)),20)
        batch={'topics':topics};sets=[{t['id'] for t in shard_topics(batch,{'shard_rank':r,'shard_count':3})} for r in range(3)]
        self.assertEqual(set.union(*sets),{t['id'] for t in topics});self.assertFalse(sets[0]&sets[1])
        with patch.dict('os.environ',{},clear=True):self.assertEqual(devices({'devices':'auto'},query=lambda:'0, GPU-a\n1, GPU-b'),['0','1'])
        for masked in ('','-1'):
            with patch.dict('os.environ',{'CUDA_VISIBLE_DEVICES':masked}):
                with self.assertRaisesRegex(ValueError,'masks all'):devices({'devices':'auto'},query=lambda:'0, GPU-a')
        with patch.dict('os.environ',{'CUDA_VISIBLE_DEVICES':'GPU-b'}):
            self.assertEqual(devices({'devices':'auto'},query=lambda:'0, GPU-a\n1, GPU-b'),['1'])
            with self.assertRaises(ValueError):devices({'devices':[0]},query=lambda:'0, GPU-a\n1, GPU-b')
        with self.assertRaises(ValueError):devices({'devices':[0],'renders_per_device':2})

    def test_actual_process_claim_recovery_and_owned_stop(self):
        import subprocess,os,socket
        from experiments.device_scheduler import Claims,stop_children
        from planner_harness.owned_process import birth
        topics=[{'id':str(i)} for i in range(12)]
        batch={'sha256':'plan','topics':topics,'arms':['none']};save(self.output/'batch.json',batch)
        queue=Claims(self.output/'queue.sqlite3',topics,'plan','parent')
        fixture=self.root/'claim_worker.py'
        fixture.write_text("""import sys,os,socket,time,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from experiments.device_scheduler import Claims
from planner_harness.owned_process import birth
from planner_harness.common import save
output=Path(sys.argv[2]);topics=[{'id':str(i)} for i in range(12)]
owner=socket.gethostname()+':'+str(os.getpid())+':'+str(birth(os.getpid()))+':fixture'
queue=Claims(output/'queue.sqlite3',topics,'plan',owner)
seen=[]
while True:
 t=queue.next()
 if t is None:break
 seen.append(t['id']);time.sleep(.015)
 if sys.argv[3]=='crash':save(output/'dead-claim.json',{'topic':t['id']});os._exit(7)
 queue.finish(t['id'],'settled')
save(output/(sys.argv[3]+'.json'),{'pid':os.getpid(),'topics':seen,'warm_initializations':1})
""")
        children=[subprocess.Popen([sys.executable,'-B',str(fixture),str(ROOT/'src'),str(self.output),'crash'])]
        children[0].wait(timeout=10)
        self.assertEqual(children[0].returncode,7)
        children.extend(subprocess.Popen([sys.executable,'-B',str(fixture),str(ROOT/'src'),str(self.output),name]) for name in ('a','b'))
        for child in children:child.wait(timeout=10)
        dead=load(self.output/'dead-claim.json')['topic']
        rows=queue.rows();self.assertEqual(sum(r['status']=='claimed' for r in rows),1)
        queue.recover(self.output);self.assertEqual(next(r['status'] for r in queue.rows() if r['topic']==dead),'pending')
        # A complete settlement recovers a dead claim. A submitted unresolved
        # operation remains isolated rather than requeued.
        claimed=queue.next();save(self.output/'methods'/claimed['id']/'none/settlement.json',{'batch_sha256':'plan'})
        with queue.connect() as db:db.execute('UPDATE tasks SET owner=? WHERE id=?',(socket.gethostname()+':999999:never:fixture',claimed['id']))
        queue.recover(self.output);self.assertEqual(next(r['status'] for r in queue.rows() if r['topic']==dead),'settled_from_receipts')
        # A dead claim with a submitted operation is held for recovery.
        unknown_topic='11' if dead!='11' else '10'
        with queue.connect() as db:db.execute('UPDATE tasks SET status="claimed",owner=? WHERE id=?',(socket.gethostname()+':999999:never:fixture',unknown_topic))
        save(self.output/'accounting/ledger.json',{'operations':{'submitted':{'topic':unknown_topic,'lane':'none','status':'in_flight_unknown'}}})
        queue.recover(self.output);self.assertEqual(next(r['status'] for r in queue.rows() if r['topic']==unknown_topic),'recovery_required')
        # Parent stop controls recorded process identity, leaving unrelated one alive.
        owned=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],start_new_session=True)
        unrelated=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],start_new_session=True)
        self.addCleanup(lambda:unrelated.poll() is None and unrelated.terminate())
        stream=(self.root/'owned.log').open('ab')
        stop_children([(owned,stream,'fixture',birth(owned.pid))],self.output)
        self.assertIsNotNone(owned.poll());self.assertIsNone(unrelated.poll())
        unrelated.terminate();unrelated.wait(timeout=3)

    def test_shard_export_import_preserves_media_and_missing_planned_positions(self):
        self.prepare(methods=['direct','none'],best_of_n=None,splits=['train'],prompt_forms=['short'])
        save(self.output/'host.json',{'shard_rank':0,'shard_count':1})
        original=results.import_video(self.repo,self.registry,self.row())
        manifest=results.export_shard(self.repo,self.registry,self.output,self.root/'portable')
        imported=results.import_manifest(self.repo,self.root/'merged',manifest)
        self.assertEqual(imported[0]['video_sha256'],original['video_sha256'])
        view=results.report(self.repo,self.root/'merged')
        self.assertTrue(any(r['method']=='none' and r['status']=='missing' for r in view['results']))
        self.assertTrue(any(r['method']=='direct' and r['status']=='ready' for r in view['results']))

    def test_report_recovery_uses_capacity_ladder_and_bound_distinct_format_feedback(self):
        from planner_harness.report_call import call_report,verify_inputs,POLICY
        from planner_harness.integrity import IntegrityError
        for category in ('capacity','format'):
            class Model:
                model='fixture';reasoning_effort='high'
                def __init__(inner):inner.inputs=[]
                def predict_text(inner,**kw):
                    inner.inputs.append(kw);first=len(inner.inputs)==1
                    inner.last_finish_reason='length' if first and category=='capacity' else 'stop'
                    return ('' if category=='capacity' else '{') if first else '{"ok":true}'
            model=Model();packet={'system_prompt':'s','user_text':'{"task":"fixture"}','images':[]};directory=self.root/category
            report,binding=call_report(directory,model,packet,[],lambda value,packet:value)
            self.assertEqual([r['max_new_tokens'] for r in model.inputs],[16384,16384])
            self.assertNotEqual(model.inputs[0]['user_text'],model.inputs[1]['user_text'])
            feedback=json.loads(model.inputs[1]['user_text'])['report_recovery']['previous_attempts'][0]
            self.assertEqual(feedback['response_sha256'],sha(directory/'call/response.txt'))
            call=Path(binding['call_path']);verify_inputs(call,model,packet,[])
            sent=load(call/'input.json');sent['user_text']=packet['user_text'];save(call/'input.json',sent)
            with self.assertRaises(IntegrityError):verify_inputs(call,model,packet,[])
        self.assertEqual(POLICY['max_reserved_output_tokens'],32768)

    def test_training_full_updates_private_current_and_next_task_reads_it(self):
        import shutil
        from planner_harness.creative_knowledge import CreativeKnowledge
        from planner_harness import training_experience as tx,maintenance
        seed=self.root/'seed.json';CreativeKnowledge(ROOT,experience_mode='full').freeze(seed);snapshot=load(seed)
        for name in [*snapshot['asset_hashes'],'knowledge/source-map.json','src/planner_harness/CREATIVE_LOOP.md',
            'docs/experience-authoring-standard.md','docs/experience-usage-interface.md','docs/online-event-observation.md',
            *[f'.agents/skills/{name}/SKILL.md' for name in maintenance.SKILLS]]:
            target=self.repo/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
        before=tx.initialize(self.repo,self.output,seed);entry=snapshot['curated_catalog']['entries'][0]
        execution={'mode':'replay','experience_mode':'full','renderer':{'seed':42},
            'experience_snapshot':before['snapshot'],'experience_snapshot_sha256':before['snapshot_sha256'],
            'benchmark_metadata':{'split':'train','sample_id':'001'}}
        self.h=PlannerHarness(self.root/'training-task',loop.Scripted([loop.action('generate',input_video='source',prompt='Blue.')]),root=self.repo)
        self.h.start(self.source,self.rows[0]['prompt_short'],mode='loop',workflow='creative_loop_v1',execution=execution)
        loop.CreativeTests.respond(self)
        self.h.model=loop.Scripted([loop.action('finish',video='v1',stop_reason='budget',message='Explicit software fixture stop')]);self.h.resume()
        state_before=sha(self.h.output/'state.json');job=maintenance.enqueue(self.repo,self.output,self.h.output,split='train',topic='001-short',method='full',batch_sha256='fixture')
        text=snapshot['documents'][entry['path']]['text']+'\nPrivate training fixture: preserve this conditional distinction.\n'
        class Contributor:
            model='fixture';reasoning_effort='high'
            def __init__(inner):inner.inputs=[]
            def predict_text(inner,**kw):
                inner.inputs.append(kw)
                if len(inner.inputs)==1:return json.dumps({'action':'read','arguments':{'source':'knowledge','id':entry['id']}})
                return json.dumps({'action':'contribute','arguments':{'text':'A bounded fixture improvement, not a visual claim.',
                    'changes':[{'op':'propose_revision','id':entry['id'],'text':text,'summary':entry['summary']+' Private training fixture distinction.'}]}})
        result=tx.maintain(self.repo,self.output,self.h.output,job,{'model_calls':3,'attempts':1,'wall_seconds':30},model_factory=Contributor)
        self.assertEqual(result['status'],'activated',result);after=tx.current(self.repo,self.output)
        self.assertEqual(after['version'],1);self.assertEqual(state_before,sha(self.h.output/'state.json'))
        self.assertFalse(result['canonical_entries_changed'])
        self.assertEqual(load(after['snapshot'])['documents'][entry['path']], snapshot['documents'][entry['path']])
        activation=self.output/'training-experience/activations'/(job+'.json');activation.unlink()
        contribution=self.output/'maintenance/jobs'/job/'training-attempt-1/contribution.json'
        self.assertEqual(tx.activate(self.repo,self.output,contribution)['after'],after)
        self.assertEqual(tx.current(self.repo,self.output),after)
        self.assertNotIn('Private training fixture',snapshot['documents'][entry['path']]['text'])
        model=loop.Scripted([loop.action('read',targets=[{'id':entry['id']}]),loop.action('finish',stop_reason='budget',message='No generation in software fixture')])
        execution.update(experience_snapshot=after['snapshot'],experience_snapshot_sha256=after['snapshot_sha256'])
        second=PlannerHarness(self.root/'next-training-task',model,root=self.repo)
        second.start(self.source,self.rows[0]['prompt_long'],mode='loop',workflow='creative_loop_v1',execution=execution)
        self.assertIn('Private training fixture',json.dumps(model.inputs[-1]))
        self.assertEqual(load(second.output/'knowledge-snapshot.json')['curated_catalog']['revision'],load(after['snapshot'])['curated_catalog']['revision'])
        frozen=self.root/'test-frozen.json';immutable(frozen,load(after['snapshot']));frozen_hash=sha(frozen)
        with self.assertRaises(ValueError):maintenance.provenance(self.repo,self.h.output,'test')
        self.assertEqual(frozen_hash,sha(frozen));self.assertFalse(maintenance.eligible(self.h.output,'test'))

    def test_default_split_matrix_and_ordered_learning_claims(self):
        batch=self.prepare(methods=None,best_of_n=None)
        self.assertEqual(next(t['methods'] for t in batch['topics'] if t['split']=='train'),['none'])
        self.assertEqual(set(next(t['methods'] for t in batch['topics'] if t['split']=='test')),set(results.DEFAULT_TEST_METHODS))
        from experiments.device_scheduler import work_units,Claims
        batch=load(self.output/'batch.json');units=work_units(batch,{})
        q=Claims(self.root/'learning-queue.db',units,batch['sha256'],'worker-a')
        first=q.next();self.assertEqual(first['methods'],['none'])
        other=Claims(self.root/'learning-queue.db',units,batch['sha256'],'worker-b')
        remaining=[]
        while (topic:=other.next()) is not None:remaining.append(topic)
        self.assertFalse(any(t['split']=='train' for t in remaining))
        q.finish(first['claim_id'],'settled');self.assertEqual(q.next()['split'],'train')
        with self.assertRaises(ValueError):self.prepare(methods=['none','full'],best_of_n=None,splits=['train'])

    def test_actual_final_cli_needs_no_judge_quota_and_keeps_optional_compute_budget(self):
        import run_creative_judge as cli
        import test_resource_accounting as budget_fixture
        from evaluation.low_high import freeze_plan
        from planner_harness.video import Video
        info=Video(self.source,self.root/'cli-info').info
        freeze_plan({'track':'long'},'Make it blue.',info,self.root/'cli-plan')
        request=self.root/'request.txt';request.write_text('Make it blue.')
        policy=budget_fixture.live_policy();policy['allocations']['independent']['model_calls']=0
        for key in ['model:glm5.3flash/none','model:sonnet-5.5high/high']:policy['quotes'].pop(key,None)
        a.validate_cohort(policy)
        budget=self.root/'compute-budget.json';save(budget,policy)
        seen=[]
        def automatic(*args,**kw):
            seen.append(kw['accounting_scope'])
            if kw['accounting_scope']:a.checked(kw['accounting_scope'],require_live=True)
            return {'metrics':{}}
        for supplied in (False,True):
            args=['run_creative_judge.py','--source',str(self.source),'--candidate',str(self.source),'--request-file',str(request),
                '--plan',str(self.root/'cli-plan/plan.json'),'--output',str(self.root/('with-compute' if supplied else 'without-budget')),'--execute']
            if supplied:args+=['--budget-config',str(budget)]
            with patch.object(sys,'argv',args),patch('evaluation.creative.make_judge',return_value=object()),patch('evaluation.creative.judge_candidate',return_value={'report':{}}),patch('evaluation.final_suite.automatic',side_effect=automatic):cli.main()
        self.assertIsNone(seen[0]);self.assertIsNotNone(seen[1])

    def test_http_diagnostic_preserves_request_status_without_auth_secrets(self):
        import io,urllib.error
        from evaluation.creative import ProviderHTTPError
        from planner_harness.model_call import call_text,ModelTransportError
        body={'error':{'code':'invalid_request_error','message':'One request failed; echo plaincustomcredential99 Authorization: Bearer secret-value x-api-key: hidden-key token=hidden-token'}}
        error=ProviderHTTPError('fixture',urllib.error.HTTPError('https://example.invalid',400,'Bad request',{},io.BytesIO(json.dumps(body).encode())),secret='plaincustomcredential99')
        self.assertEqual(error.safe_diagnostic['status'],400);self.assertEqual(error.safe_diagnostic['scope'],'request')
        text=json.dumps(error.safe_diagnostic)
        for secret in ('secret-value','hidden-key','hidden-token','plaincustomcredential99'):self.assertNotIn(secret,text)
        class Model:
            model='fixture';reasoning_effort='high';requires_live_budget=True
            def predict_text(inner,**kw):raise error
        directory=self.root/'http-failure'
        with self.assertRaises(ModelTransportError) as captured:call_text(directory,Model(),'s','u',[],meter_only=True,max_new_tokens=None)
        self.assertEqual(captured.exception.http_status,400)
        self.assertEqual(load(directory/'attempts/01/failed.json')['provider_error'],error.safe_diagnostic)

    def test_provider_balance_pause_is_not_missing_score_and_explicit_recovery_reuses_request(self):
        import io,urllib.error
        from evaluation.creative import ProviderHTTPError
        from planner_harness.model_call import ProviderDispatchPaused,reopen_call
        from planner_harness.report_call import call_report
        message={'error':{'code':'new_api_error','message':'预扣费额度失败, 用户剩余额度不足'}}
        error=ProviderHTTPError('fixture',urllib.error.HTTPError('https://example.invalid',403,'Forbidden',{},io.BytesIO(json.dumps(message).encode())))
        class Model:
            model='fixture';reasoning_effort='high';requires_live_budget=True
            def __init__(inner):inner.inputs=[];inner.restored=False
            def predict_text(inner,**kw):
                inner.inputs.append(kw)
                if not inner.restored:raise error
                return '{"ok":true}'
        model=Model();directory=self.root/'balance-paused';packet={'system_prompt':'s','user_text':'u','images':[]}
        for _ in range(2):
            with self.assertRaises(ProviderDispatchPaused) as captured:call_report(directory,model,packet,[],lambda value,packet:value,usage='independent_final')
            self.assertEqual(captured.exception.provider_error['category'],'provider_balance_insufficient')
        self.assertEqual(len(model.inputs),1);self.assertFalse((directory/'unavailable.json').exists())
        reopen_call(directory/'call','Provider account replenished; original request was explicitly rejected.',1)
        model.restored=True
        result,binding=call_report(directory,model,packet,[],lambda value,packet:value,usage='independent_final')
        self.assertTrue(result['ok']);self.assertEqual(len(model.inputs),2)
        self.assertEqual(load(directory/'call/returned.json')['attempt'],2)

    def test_full_judge_resumes_balance_paused_specialty_without_repeating_events_or_main(self):
        import io,urllib.error
        from evaluation.creative import judge_candidate,ProviderHTTPError
        from evaluation.low_high import freeze_plan
        from planner_harness.model_call import ProviderDispatchPaused,reopen_call
        from planner_harness.video import Video
        info=Video(self.source,self.root/'resume-info').info
        plan=freeze_plan({'track':'long'},'Make it blue.',info,self.root/'resume-plan')
        error=ProviderHTTPError('fixture',urllib.error.HTTPError('https://example.invalid',403,'Forbidden',{},io.BytesIO(json.dumps({'error':{'code':'new_api_error','message':'预扣费额度失败, 用户剩余额度不足'}}).encode())))
        class Model:
            model='sonnet-5.5high';reasoning_effort='high';requires_live_budget=True
            def __init__(inner):inner.counts={'event':0,'main':0,'specialty':0};inner.restored=False
            def predict_text(inner,**kw):
                visible=json.loads(kw['user_text']);stage='specialty' if visible.get('stage')=='task_metrics' else 'event' if 'scope' in visible else 'main'
                inner.counts[stage]+=1
                if stage=='specialty' and not inner.restored:raise error
                return json.dumps(loop.review_fixture(kw['user_text']))
        model=Model();directory=self.root/'resumed-judge'
        with self.assertRaises(ProviderDispatchPaused):judge_candidate('Make it blue.',info,info,directory,model=model,plan=plan)
        before=dict(model.counts);self.assertFalse((directory/'task-metrics/unavailable.json').exists());self.assertFalse((directory/'judgment.json').exists())
        reopen_call(directory/'task-metrics/call','Provider account replenished; explicit resume of the refused specialty request',1)
        model.restored=True;result=judge_candidate('Make it blue.',info,info,directory,model=model,plan=plan)
        self.assertEqual(model.counts['event'],before['event']);self.assertEqual(model.counts['main'],before['main'])
        self.assertEqual(model.counts['specialty'],before['specialty']+1);self.assertEqual(result['task_metrics']['status'],'scored')
        save(ROOT/'out/loop_protocol_upgrade_20261102/final-judge-resume-proof.json',{'before':before,'after':model.counts,'result_status':result['task_metrics']['status'],
            'returned_transport_attempt':load(directory/'task-metrics/call/returned.json')['attempt'],'permanent_unavailable':(directory/'task-metrics/unavailable.json').exists(),
            'sources':{name:sha(ROOT/name) for name in ['src/evaluation/creative.py','src/planner_harness/model_call.py','src/planner_harness/report_call.py']},'paid_calls':0,'gpu_jobs':0})

    def test_independent_final_is_live_meter_only_without_budget_or_output_cap(self):
        from planner_harness.report_call import call_report,verify_inputs,FINAL_POLICY
        from evaluation.creative import ParateraJudge,SonnetJudge
        from unittest.mock import patch
        class Model:
            model='fixture';reasoning_effort='high';requires_live_budget=True
            def __init__(inner):inner.inputs=[]
            def predict_text(inner,**kw):
                inner.inputs.append(kw);inner.last_usage={'input_tokens':12,'output_tokens':30000};return '{"ok":true}'
        packet={'system_prompt':'s','user_text':'{"task":"fixture"}','images':[]};model=Model();directory=self.root/'uncapped'
        with patch('planner_harness.accounting.discover',side_effect=AssertionError('No final budget discovery')),patch('planner_harness.accounting.reserve',side_effect=AssertionError('No quota reservation')):
            report,binding=call_report(directory,model,packet,[],lambda value,packet:value,usage='independent_final')
        self.assertIsNone(model.inputs[0]['max_new_tokens'])
        receipt=load(directory/'call/attempts/01/result.json');self.assertEqual(receipt['accounting_mode'],'live_meter_only')
        self.assertEqual(receipt['usage']['output_tokens'],30000);self.assertIsNone(receipt['output_budget'])
        self.assertNotIn('max_tokens',ParateraJudge.build_payload('s','u',[],None))
        self.assertEqual(SonnetJudge.build_payload('s','u',[],None)['max_tokens'],128000)
        self.assertIsNone(FINAL_POLICY['max_reserved_output_tokens']);verify_inputs(Path(binding['call_path']),model,packet,[])

    def test_final_main_unknown_reference_only_drops_its_dimension(self):
        from evaluation import final_projection as fp
        from critic_harness.one_shot import prepare_request,frozen_profile
        from planner_harness.video import Video
        info=Video(self.source,self.root/'info').info
        packet,_=prepare_request('Make it blue.','candidate',{'source':info,'candidate':info},self.root/'main-evidence',frozen_profile())
        from evaluation.low_high import PROTOCOL
        visible=json.loads(packet['user_text']);visible['protocol_id']=PROTOCOL;packet['user_text']=json.dumps(visible)
        raw=loop.review_fixture(packet['user_text']);raw.pop('task_diagnostics',None)
        raw['main_scores']['aesthetic_coherence']['evidence_refs']=['candidate:missing:999']
        projected,errors=fp.project(raw,packet)
        self.assertEqual(len(errors),1);self.assertEqual(projected['main_scores']['aesthetic_coherence']['status'],'unknown')
        self.assertEqual(projected['main_scores']['instruction_adherence'],raw['main_scores']['instruction_adherence'])
        class Model:
            model='fixture';reasoning_effort='high'
            def predict_text(inner,**kw):return json.dumps(raw)
        directory=self.root/'main-call';report,binding,projection=fp.evaluate(directory,Model(),packet,[r['path'] for r in packet['images']])
        result={'report':report,'answer_binding':binding,'main_projection':projection}
        fp.verify(directory,result,packet,Model())
        result['answer_binding']={**binding,'response_sha256':'forged'};result['main_projection']['answer_binding']=result['answer_binding']
        save(directory/'final-main-projection.json',result['main_projection'])
        with self.assertRaisesRegex(ValueError,'binding changed'):fp.verify(directory,result,packet,Model())

    def test_final_diagnostics_project_only_invalid_fields_and_verify_original_answer(self):
        from evaluation import task_metrics as tm
        from evaluation.low_high import prepare_final, freeze_plan
        from planner_harness.video import Video
        info=Video(self.source,self.root/'info').info
        plan=freeze_plan({'track':'long'},'Make the room blue.',info,self.root/'plan')
        packet,_=prepare_final('Make the room blue.',info,info,self.root/'evidence',plan=plan)
        class Model:
            model='fixture';reasoning_effort='high'
            def __init__(inner):inner.calls=[]
            def predict_text(inner,**kw):
                inner.calls.append(1);value=loop.review_fixture(kw['user_text']);visible=json.loads(kw['user_text'])
                refs=[e['id'] for e in visible['evidence'] if e['video_id']=='candidate']
                value['unrequested_damage']={'status':'scored','severity':'minor','reason':'Fixture missing source attribution','evidence_refs':refs}
                value['aesthetics']['color_texture']['score']=9
                return json.dumps(value)
        model=Model();directory=self.root/'diagnostics'
        result=tm.evaluate(packet,directory,model)
        self.assertEqual(len(model.calls),1);self.assertEqual(result['status'],'scored')
        self.assertEqual(result['report']['unrequested_damage']['status'],'unknown')
        self.assertEqual(result['report']['aesthetics']['color_texture']['status'],'unknown')
        self.assertEqual(result['report']['aesthetics']['composition_lighting']['score'],3)
        self.assertEqual(result['report']['items'][0]['completion']['label'],'pass')
        self.assertEqual(len(result['field_projection']['errors']),2)
        self.assertEqual(tm.verify(directory,model,expected_packet=packet),result)
        tampered=copy.deepcopy(result);tampered['answer_binding']['response_sha256']='forged'
        projection=load(directory/'field-projection.json');original_projection=copy.deepcopy(projection)
        projection['answer_binding']=tampered['answer_binding'];save(directory/'field-projection.json',projection);save(directory/'result.json',tampered)
        with self.assertRaisesRegex(ValueError,'projection changed'):tm.verify(directory,model,expected_packet=packet)
        save(directory/'field-projection.json',original_projection)
        result['field_projection']['errors']=[];save(directory/'result.json',result)
        with self.assertRaisesRegex(ValueError,'projection changed'):tm.verify(directory,model,expected_packet=packet)

    def test_source_group_itt_distinguishes_missing_outputs_from_unknown_judge(self):
        from evaluation.statistics import summarize
        rows=[]
        for form in ('short','long'):
            rows.append({'split':'test','seed':42,'judge':'fixture','comparison':'pe-loop_final__to__none_final','source_id':'s','source_group':'g','length':form,
                'availability':{'left':True,'right':True},'result':None})
        report=summarize(rows)['by_judge']['fixture']['pe-loop_final__to__none_final']['task_completion']
        self.assertEqual(report['planned_source_groups'],1);self.assertEqual(report['left_itt_source_mean_bounds'],[0,1]);self.assertIsNone(report['paired_permutation_p'])
        for row in rows:row['availability']['right']=False
        report=summarize(rows)['by_judge']['fixture']['pe-loop_final__to__none_final']['task_completion']
        self.assertEqual(report['left_itt_source_mean'],1);self.assertEqual(report['administrative_missing_output_assignments'],2)

if __name__=='__main__':unittest.main()
