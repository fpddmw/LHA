"""Offline accounting, ownership and real dispatch boundary tests. No API/GPU."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from planner_harness import accounting as a
from planner_harness.common import load,save
from planner_harness.integrity import IntegrityError
from planner_harness.resources import ResourceExhausted
from planner_harness.execution import signature


def live_policy():
    lane={**a.LIMITS,'model_calls':100,'render_requests':8,'compute_requests':1,'tokens':4000000,'wall_seconds':20,'amount':'1000'}
    total={k:sum(v[k] for v in [lane]*4) for k in lane if k!='amount'}
    total['amount']='4000'
    return {'version':a.VERSION,'mode':'live','currency':'CNY','batch':{**{k:v*2 for k,v in total.items() if k!='amount'},'wall_seconds':1000,'amount':'8000'},'topic':total,
        'allocations':{k:copy.deepcopy(lane) for k in a.LANES},'max_call_seconds':1,
        'quotes':{k:{'currency':'CNY','unit':'request','max_amount':'1','source':'offline-test quotation; not a real price','quoted_at':'2026-11-02'} for k in a.REQUIRED_QUOTES}}


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.threads=[];self.releases=[]
    def tearDown(self):
        for e in self.releases:e.set()
        for t in self.threads:t.join(3)
        deadline=time.monotonic()+3
        while a.active(self.root/'accounting') and time.monotonic()<deadline:time.sleep(.01)
    def scope(self,p=None,lane='full',topic='one'):
        a.install(self.root/'accounting',p)
        return a.scope(self.root/'accounting',topic,lane)
    def test_offline_unpriced_lane_allocation_keeps_amount_unknown(self):
        p=live_policy();p['mode']='offline';p.pop('quotes');p.pop('currency')
        p['batch']['amount']=p['topic']['amount']=None
        for v in p['allocations'].values():v['amount']=None
        b=self.scope(p);a.invoke(b,'one','render','render:bernini',lambda:{})
        self.assertIsNone(a.summary(b['root'])['total_amount'])
    def test_live_required_fields_never_infer_prices_or_allowance(self):
        for change in ('missing','currency','quote','amount','lane'):
            p=live_policy()
            if change=='missing':p=None
            elif change=='currency':p['currency']=''
            elif change=='quote':del p['quotes'][a.REQUIRED_QUOTES[0]]
            elif change=='lane':del p['allocations']['none']
            else:p['batch']['amount']=None
            with self.assertRaises(a.BudgetConfigurationError):a.validate_policy(p,require_live=True,required_quotes=a.REQUIRED_QUOTES)
    def test_concurrent_scope_binding_is_idempotent(self):
        a.install(self.root/'accounting');errors=[]
        def bind():
            try:a.topic_scope(self.root,'one')
            except Exception as exc:errors.append(exc)
        ts=[threading.Thread(target=bind) for _ in range(8)]
        for t in ts:t.start()
        for t in ts:t.join(2)
        self.assertFalse(errors);self.assertTrue(all(not t.is_alive() for t in ts))
    def test_api_scoped_call_keeps_real_usage_without_artificial_output_cap(self):
        from vlm.openrouter import OpenRouterVisionModel
        with patch.dict('os.environ',{'OPENROUTER_API_KEY':'software-fixture'}):
            model=OpenRouterVisionModel()
        self.assertEqual(model.runtime_identity()['backend'],'openrouter_api')
        self.assertEqual(model.output_limit_mode,'provider_default')
        self.assertFalse(model.budget_capabilities()['hard_output_tokens'])


    def test_unpriced_replay_counts_once_and_never_claims_money(self):
        b=self.scope();calls=[]
        self.assertEqual(a.invoke(b,'render1','render','render:bernini',lambda:calls.append(1) or {'ok':1}),{'ok':1})
        self.assertEqual(a.invoke(b,'render1','render','render:bernini',lambda:self.fail('repeated')),{'ok':1})
        s=a.summary(b['root']);self.assertEqual(calls,[1]);self.assertIsNone(s['total_amount']);self.assertFalse(s['invoice_ceiling_verified'])
        self.assertEqual(s['reserved_or_settled_totals']['render_requests'],1)
    def test_decimal_settlement_and_breach_are_not_clamped(self):
        p=live_policy();p['quotes'][a.REQUIRED_QUOTES[0]].update(input_per_million='1000000',output_per_million='1000000')
        b=self.scope(p)
        a.invoke(b,'m','model',a.REQUIRED_QUOTES[0],lambda:{},tokens=1,usage_getter=lambda:{'input_tokens':2,'output_tokens':1})
        s=a.summary(b['root']);self.assertEqual(s['total_amount'],'3');self.assertEqual(len(s['breaches']),1)
        with self.assertRaises(ResourceExhausted):a.invoke(b,'next','model',a.REQUIRED_QUOTES[0],lambda:self.fail('breached'))
    def test_failed_external_cost_stays_held_and_not_zero(self):
        b=self.scope(live_policy())
        with self.assertRaises(ConnectionError):a.invoke(b,'bad','model',a.REQUIRED_QUOTES[0],lambda:(_ for _ in ()).throw(ConnectionError('fixture')))
        r=a.operation(b,'bad');self.assertEqual(r['charged_amount'],'1');self.assertIsNone(r['settled_amount'])
        self.assertIn('bad',a.summary(b['root'])['unknown_cost_operations'])
    def test_double_thread_same_key_dispatches_once(self):
        b=self.scope();entered=threading.Event();release=threading.Event();self.releases.append(release);calls=[];results=[]
        def fn():calls.append(1);entered.set();release.wait(2);return {'one':1}
        def first():results.append(a.invoke(b,'same','render','render:bernini',fn))
        t=threading.Thread(target=first);self.threads.append(t);t.start();self.assertTrue(entered.wait(1))
        with self.assertRaises(a.ExternalExecutionUnknown):a.invoke(b,'same','render','render:bernini',fn)
        release.set();t.join(2)
        self.assertEqual(a.invoke(b,'same','render','render:bernini',fn),{'one':1});self.assertEqual(calls,[1]);self.assertEqual(results,[{'one':1}])
    def test_stale_reservation_rechecked_after_execution_lease(self):
        b=self.scope();old=a.reserve(b,'same','model','fixture');a.invoke(b,'same','model','fixture',lambda:{'one':1})
        with patch.object(a,'reserve',return_value=old):self.assertEqual(a.invoke(b,'same','model','fixture',lambda:self.fail('stale dispatch')),{'one':1})
    def test_before_submit_failure_releases_lease_and_records_zero_dispatch(self):
        b=self.scope();calls=[]
        with self.assertRaises(ValueError):a.invoke(b,'bad','model','fixture',lambda:calls.append(1),before_submit=lambda:(_ for _ in ()).throw(ValueError('not submitted')))
        self.assertEqual(calls,[]);self.assertEqual(a.operation(b,'bad')['status'],'not_submitted');self.assertEqual(a.active(b['root']),[])
        from planner_harness.lock import RunLock
        with RunLock(Path(b['root'])/'operations'/signature({'id':'bad'})/'execution-owner'):pass
    def test_not_submitted_replay_is_terminal_known_refusal_with_zero_charge(self):
        b=self.scope(live_policy());calls=[]
        with self.assertRaises(ValueError):
            a.invoke(b,'refused','model',a.REQUIRED_QUOTES[0],lambda:calls.append(1),tokens=20,
                before_submit=lambda:(_ for _ in ()).throw(ValueError('pre-submit fixture')))
        old=a.operation(b,'refused')
        for _ in range(3):
            with self.assertRaises(a.SubmissionRefused) as caught:
                a.invoke(b,'refused','model',a.REQUIRED_QUOTES[0],lambda:calls.append(1),tokens=20)
            self.assertFalse(caught.exception.outcome_unknown);self.assertFalse(caught.exception.retryable)
        self.assertFalse(calls);self.assertEqual(a.operation(b,'refused'),old)
        self.assertEqual(a.summary(b['root'])['reserved_or_settled_totals'],
            {'model_calls':0,'render_requests':0,'compute_requests':0,'tokens':0,'amount':'0'})
        # Exercise the lock-after-reserve path with a formerly reserved record.
        stale={**old,'status':'reserved'}
        with patch.object(a,'reserve',return_value=stale):
            with self.assertRaises(a.SubmissionRefused):a.invoke(b,'refused','model',a.REQUIRED_QUOTES[0],lambda:calls.append(1))
        self.assertFalse(calls)
    def test_model_replay_does_not_reclassify_known_non_submission(self):
        from planner_harness.model_call import call_text
        calls=[]
        class Model:
            model='gpt-6.1-sol';reasoning_effort='high';requires_live_budget=True
            def predict_text(self,**kw):calls.append(1);raise AssertionError('must not submit')
        b=self.scope(live_policy());client=a.attach(Model(),b);directory=self.root/'model-refused';entry=directory/'attempts/01'
        key=str(entry.resolve());a.reserve(b,key,'model',a.REQUIRED_QUOTES[0],tokens=10)
        a.transition(b,key,'not_submitted',charged_tokens=0,charged_amount='0',cost_status='deadline_before_dispatch')
        save(entry/'submitted.json',{'audit':'local pre-submit intent, not external dispatch'})
        for _ in range(3):
            with self.assertRaises(a.SubmissionRefused) as caught:call_text(directory,client,'s','u',[],attempts=3,retry_delay=0)
            self.assertFalse(caught.exception.outcome_unknown);self.assertFalse(caught.exception.retryable)
        self.assertFalse(calls);self.assertFalse((entry/'unknown.json').exists())
        self.assertEqual(a.operation(b,key)['charged_amount'],'0');self.assertFalse((directory/'attempts/02').exists())
    def test_service_started_intent_keeps_known_non_submission_on_replay(self):
        from server_runtime.queue import Queue
        from server_runtime.service import Service
        b=self.scope(live_policy());calls=[];directory=self.root/'known-refusal-service';folder=directory/'direct/topic'
        body={'id':'known-refused','kind':'generate','mode':'live','accounting_scope':b,
              'payload':{'renderer':{'backend':'bernini'}}}
        request={**body,'sha256':signature(body)};save(folder/'request.json',request)
        save(folder/'render-started.json',{'request_sha256':request['sha256']})
        a.reserve(b,request['sha256'],'render','render:bernini')
        a.transition(b,request['sha256'],'not_submitted',charged_tokens=0,charged_amount='0',cost_status='deadline_before_dispatch')
        config={'workflow':'creative_loop_v1','accounting_root':b['root'],'budget':live_policy(),
            'planner':{'model':'gpt-6.1-sol','reasoning_effort':'high'},'critic':{'model':'gpt-6.1-sol','reasoning_effort':'high'}}
        service=Service(Queue(directory/'queue.sqlite3'),directory,ROOT,config,
            renderer=lambda *args:calls.append(1) or {})
        job={'kind':'tool','payload':{'request':str(folder/'request.json'),'request_sha256':request['sha256']}}
        for _ in range(3):
            response=service(job,directory/'job')['response']
            self.assertEqual(response['status'],'failed');self.assertEqual(response['failure_kind'],'resource_exhausted')
            self.assertIs(response['outcome_unknown'],False);self.assertIs(response['retryable'],False)
        self.assertFalse(calls);self.assertEqual(a.operation(b,request['sha256'])['charged_amount'],'0')
    def test_expired_during_pre_submit_is_zero_calls(self):
        p={'version':a.VERSION,'mode':'offline','batch':{'wall_seconds':1},'topic':{'wall_seconds':1}}
        b=self.scope(p);calls=[]
        def before():time.sleep(1.02)
        with self.assertRaises(ResourceExhausted):a.invoke(b,'expired','model','fixture',lambda:calls.append(1),before_submit=before)
        self.assertFalse(calls);self.assertEqual(a.operation(b,'expired')['status'],'not_submitted')
    def test_lane_deadline_bounds_active_wait(self):
        p=live_policy();p['max_call_seconds']=10;p['allocations']['full']['wall_seconds']=1
        b=self.scope(p);release=threading.Event();self.releases.append(release);start=time.monotonic()
        with self.assertRaises(a.ExternalExecutionUnknown):a.invoke(b,'slow','render','render:bernini',lambda:release.wait(3) or {})
        self.assertLess(time.monotonic()-start,1.5);self.assertTrue(a.active(b['root']));release.set()
    def test_native_timeout_retains_ownership_and_late_result_no_retry(self):
        p={'version':a.VERSION,'mode':'offline','max_call_seconds':.04};b=self.scope(p);release=threading.Event();self.releases.append(release);calls=[]
        def fn():calls.append(1);release.wait(2);return {'late':1}
        with self.assertRaises(a.ExternalExecutionUnknown):a.invoke(b,'slow','render','render:bernini',fn)
        self.assertTrue(a.active(b['root']));self.assertEqual(a.operation(b,'slow')['status'],'in_flight_unknown')
        with self.assertRaises(a.ExternalExecutionUnknown):a.invoke(b,'slow','render','render:bernini',fn)
        release.set()
        deadline=time.monotonic()+2
        while a.active(b['root']) and time.monotonic()<deadline:time.sleep(.01)
        self.assertEqual(a.operation(b,'slow')['status'],'late_complete');self.assertEqual(a.invoke(b,'slow','render','render:bernini',fn),{'late':1});self.assertEqual(calls,[1])
    def test_ledger_tampering_is_hard_integrity_failure(self):
        b=self.scope();a.invoke(b,'one','model','fixture',lambda:{})
        path=Path(b['root'])/'ledger.json';original=load(path)
        for field in ('operations','topics','events'):
            damaged=copy.deepcopy(original)
            if field=='operations':damaged[field]['one']['charged_tokens']=999
            elif field=='topics':damaged[field]['one']['started_unix']=0
            else:damaged[field][0]['details']['target']='tampered'
            save(path,damaged)
            with self.assertRaises(IntegrityError):a.summary(b['root'])
        save(path,original)
    def test_lanes_and_serial_topic_admission_protect_later_arm(self):
        p=live_policy();p['allocations']['full']['render_requests']=1;p['allocations']['none']['render_requests']=1
        b=self.scope(p);a.admit_topic(b)
        a.invoke(b,'f','render','render:bernini',lambda:{})
        with self.assertRaises(ResourceExhausted):a.invoke(b,'f2','render','render:bernini',lambda:self.fail('full overused'))
        a.invoke(a.scope(b['root'],'one','none'),'n','render','render:bernini',lambda:{})
        with self.assertRaises(a.BudgetConfigurationError):a.admit_topic(a.scope(b['root'],'two'))
        a.close_topic(b);a.admit_topic(a.scope(b['root'],'two'))
    def test_cohort_rejects_undersized_or_unequal_lane_plan(self):
        p=live_policy();a.validate_cohort(p)
        p['allocations']['none']['model_calls']=99
        self.assertIsNone(a.validate_cohort(p)['allocations']['none']['model_calls'])
        p=live_policy();p['allocations']['none']['amount']='999999'
        with self.assertRaises(a.BudgetConfigurationError):a.validate_cohort(p)
    def test_model_metadata_reset_and_all_stages_share_ledger(self):
        from planner_harness.model_call import call_text
        class Model:
            model='fixture';reasoning_effort=None;last_usage={'total_tokens':999};last_provider_response={'stale':1}
            def predict_text(self,**kw):
                if self.last_usage or self.last_provider_response:raise AssertionError('stale metadata')
                self.last_usage={'total_tokens':3};return '{}'
        b=self.scope();m=a.attach(Model(),b)
        for stage in ('planner','critic-selection','critic-event','critic-report','source-plan','final-event','final-score','pairwise'):
            folder=self.root/stage
            self.assertEqual(call_text(folder,m,'s','u',[],attempts=1),'{}')
            self.assertEqual(call_text(folder,m,'s','u',[],attempts=1),'{}')
        a.run_compute('compute:temporal',{'input':'fixture'},lambda:{'measured':True},binding=b)
        totals=a.summary(b['root'])['reserved_or_settled_totals'];self.assertEqual(totals['model_calls'],8);self.assertEqual(totals['tokens'],24);self.assertEqual(totals['compute_requests'],1)
    def test_real_model_rejects_unbound_before_dispatch(self):
        from planner_harness.model_call import call_text
        class Model:
            model='real-provider';requires_live_budget=True
            def predict_text(self,**kw):raise AssertionError('called live')
        with self.assertRaises(a.BudgetConfigurationError):call_text(self.root/'no-budget',Model(),'s','u',[])
    def test_reopen_unknown_call_refuses_blind_submission(self):
        from planner_harness.model_call import reopen_call
        d=self.root/'call';save(d/'input.json',{});save(d/'attempts/01/submitted.json',{});save(d/'attempts/01/unknown.json',{})
        with self.assertRaises(ValueError):reopen_call(d,'new permission alone does not settle original')
    def test_resident_close_has_bounded_wait_without_kill(self):
        from planner_harness.supervisor import ResidentWorker
        child=subprocess.Popen([sys.executable,'-B','-c','import time;time.sleep(.4)'],start_new_session=True)
        worker=ResidentWorker.__new__(ResidentWorker);worker.process=child;worker.directory=self.root/'worker';worker.directory.mkdir()
        start=time.monotonic();worker.close(wait_seconds=.01)
        self.assertLess(time.monotonic()-start,.2);self.assertIsNone(child.poll());self.assertFalse(load(worker.directory/'retained.json')['resource_released']);child.wait(timeout=2)
    def test_real_idle_worker_does_not_consume_started_markers(self):
        # Child imports the real worker main; runtime calls are deterministic stubs.
        worker=self.root/'out/supervised-workers/0';save(worker/'commands/t__full.json',{'topic':{'id':'t'},'arm':'full'});save(self.root/'host.json',{})
        code="""import sys,time
from pathlib import Path
sys.path[:0]=[sys.argv[1]+'/src',sys.argv[1]+'/scripts']
import experiments.creative_benchmark as b
b.init_worker=lambda *a:None
b.run_arm=lambda topic,arm:{'topic':topic['id'],'arm':arm}
import accounting_worker
sys.argv=['worker','--root',sys.argv[1],'--output',sys.argv[2],'--device','0','--host',sys.argv[3]]
accounting_worker.main()"""
        child=subprocess.Popen([sys.executable,'-B','-c',code,str(ROOT),str(self.root/'out'),str(self.root/'host.json')])
        deadline=time.monotonic()+4
        try:
            while not (worker/'results/t__full.json').exists() and time.monotonic()<deadline:time.sleep(.02)
            self.assertTrue((worker/'results/t__full.json').exists());time.sleep(.15)
            self.assertEqual([p.name for p in (worker/'commands').glob('*.json')],['t__full.json'])
            self.assertEqual([p.name for p in (worker/'started').glob('*.json')],['t__full.json'])
            self.assertEqual([p.name for p in (worker/'results').glob('*.json')],['t__full.json'])
        finally:save(worker/'stop-request.json',{});child.wait(timeout=5)
    def test_real_engine_timeout_returns_while_device_lock_stays_owned(self):
        import test_planner_harness as fixture
        import test_creative_loop as creative
        from server_runtime.queue import Queue
        from server_runtime.service import Service
        from server_runtime.engine import Engine
        from planner_harness.delivery import verify_settlement
        from planner_harness.lock import RunLock
        helper=fixture.Tests();helper.setUp();self.addCleanup(helper.tearDown)
        release=threading.Event();self.releases.append(release);calls=[]
        directory=self.root/'engine';device=self.root/'device'
        queue=Queue(directory/'queue.sqlite3',{'gpu':1,'llm':1,'cpu':1})
        model=creative.Scripted([creative.action('generate',input_video='source',prompt='Blue.')])
        def renderer(job,folder):
            with RunLock(device):calls.append(1);release.wait(3)
            return {'fixture':'late result retained only by accounting'}
        cfg={'workflow':'creative_loop_v1','planner':{'model':'gpt-6.1-sol','reasoning_effort':'high'},
             'critic':{'model':'gpt-6.1-sol','reasoning_effort':'high'},
             'budget':{'version':a.VERSION,'mode':'offline','max_call_seconds':.08}}
        service=Service(queue,directory,ROOT,cfg,model_factory=lambda role:model,renderer=renderer)
        task={'id':'slow','workflow':'creative_loop_v1','source':str(helper.source),'source_sha256':__import__('planner_harness.common',fromlist=['sha']).sha(helper.source),
              'request':'Change color.','max_turns':3,'execution':{'mode':'live','renderer':{'backend':'bernini'}}}
        service.submit(task);started=time.monotonic();Engine(queue,directory,service,service.expand,interval=.01).run(once=True)
        self.assertLess(time.monotonic()-started,5);self.assertEqual(verify_settlement(directory/'tasks/slow/run')['outcome'],'execution_unknown')
        self.assertEqual(calls,[1]);self.assertEqual(len(model.inputs),1);self.assertTrue(a.active(service.accounting_root))
        with self.assertRaises(RuntimeError):
            with RunLock(device):self.fail('device falsely released')
        self.assertTrue((directory/'resources-retained.json').exists());release.set()
        deadline=time.monotonic()+3
        while a.active(service.accounting_root) and time.monotonic()<deadline:time.sleep(.01)
        self.assertFalse(a.active(service.accounting_root))
    def test_shared_plan_missing_preserves_unknown_and_budget_reason(self):
        import test_planner_harness as fixture
        from planner_harness.common import sha
        from planner_harness.video import Video
        from experiments.creative_benchmark import cache_judgment
        helper=fixture.Tests();helper.setUp();self.addCleanup(helper.tearDown)
        source=Video(helper.source,self.root/'video').info
        topic={'id':'one','source':str(helper.source),'source_sha256':source['sha256'],'request':'Change color.'}
        for reason in ('source_plan_execution_unknown','source_plan_budget_exhausted'):
            out=self.root/reason;unavailable=out/'unavailable.json';save(unavailable,{'reason':reason})
            body={'status':'missing','reason':reason,'source_sha256':source['sha256'],
                'request_sha256':signature({'text':topic['request']}),'unavailable_path':str(unavailable),'unavailable_sha256':sha(unavailable)}
            plan={**body,'sha256':signature(body)}
            row=cache_judgment(ROOT,out,topic,source,source_plan=(source,plan))
            self.assertEqual(row['result']['reason'],reason)
            self.assertIsNone(row['result']['report'])
    def test_outer_scoring_close_does_not_wait_for_native_call(self):
        from creative_benchmark_schedule import Scoring
        b=self.scope({'version':a.VERSION,'mode':'offline','max_call_seconds':.03});release=threading.Event();self.releases.append(release)
        scoring=Scoring(ROOT,self.root)
        future=scoring.pools[next(iter(scoring.pools))].submit(a.invoke,b,'slow','model','fixture',lambda:release.wait(3) or {})
        with self.assertRaises(a.ExternalExecutionUnknown):future.result(timeout=1)
        start=time.monotonic();scoring.close();self.assertLess(time.monotonic()-start,.3);self.assertTrue(a.active(b['root']));release.set()


if __name__=='__main__':unittest.main()
