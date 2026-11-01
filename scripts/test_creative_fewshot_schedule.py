"""Focused offline checks for the approved early/five-position scheduling adapter."""
import copy
from pathlib import Path
import sys
import signal
import sqlite3
import threading
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import creative_fewshot_schedule as schedule
from planner_harness.common import load, save, sha
from planner_harness.execution import signature
from test_creative_fewshot import BatchTests, Judge, SonnetFixture


class ScheduleTests(unittest.TestCase):
    setUp,tearDown=BatchTests.setUp,BatchTests.tearDown
    spec,receipt=BatchTests.spec,BatchTests.receipt

    def prepare(self,output):
        save(output/'profile.json',{'software_fixture':True})
        save(output/'batch.json',{'profile_sha256':'fixture'})

    def test_early_first_requires_matching_receipt_and_hash(self):
        topic=self.spec();output=self.root/'early';self.prepare(output)
        run=output/'workers/0/tasks/first__full/run'
        video={**topic['source_info'],'job_id':'render-1'}
        request={'id':'render-1','kind':'generate','payload':{'fixture':True}}
        request['sha256']=signature(request)
        save(run/'jobs/render-1/request.json',request)
        response={'status':'complete','request_sha256':request['sha256'],'payload':{'video':video}}
        save(run/'jobs/render-1/response.json',response)
        save(run/'state.json',{'videos':{'source':topic['source_info'],'v1':video},'status':'waiting_tool'})
        self.assertEqual(set(schedule.eligible(ROOT,output,topic)),{'full_first'})
        response['request_sha256']='incorrect';save(run/'jobs/render-1/response.json',response)
        with self.assertRaises(ValueError):schedule.eligible(ROOT,output,topic)
        response['request_sha256']=request['sha256'];response['payload']['video']['sha256']='incorrect'
        save(run/'jobs/render-1/response.json',response)
        with self.assertRaises(ValueError):schedule.eligible(ROOT,output,topic)

    def test_intermediates_retained_unscored_resume_deduplicates_and_gate_holds(self):
        topic=self.spec();second={**topic,'id':'second','request':'Another task.'}
        output=self.root/'batch';self.prepare(output)
        calls=[];Judge.calls=0;SonnetFixture.calls=0
        intermediate=self.root/'intermediate.mp4';intermediate.write_bytes(b'unscored software fixture')
        def execute(t,arm):
            calls.append((t['id'],arm))
            if t['id']=='second':self.assertTrue((output/'topics/first/archive-manifest.json').exists())
            row=self.receipt(t,arm)
            if arm=='full':
                row['videos']['v2']={**t['source_info'],'path':str(intermediate),'sha256':sha(intermediate)}
                row['sha256']=signature({k:v for k,v in row.items() if k!='sha256'})
            return row
        manifest={'topics':[topic,second],'profile_sha256':'fixture'}
        clients={'glm5.3flash':Judge(),'sonnet-5.5high':SonnetFixture()}
        with patch.object(schedule,'verify_batch',return_value=manifest):
            result=schedule.advance(ROOT,output,execute,judges=clients,poll_seconds=.001)
            self.assertEqual(result['status'],'complete')
            self.assertEqual((Judge.calls,SonnetFixture.calls),(2,2))
            self.assertEqual(len(calls),6)
            text=(output/'topics/first/archive/index.html').read_text()
            self.assertIn('videos/full/v2.mp4',text)
            self.assertIn('not independently scored',text)
            scope=load(output/'topics/first/archive/scoring-scope.json')
            self.assertEqual(scope['unscored_intermediates']['full'],['v2'])
            self.assertFalse(any(load(p)['output_sha256']==sha(intermediate) for p in (output/'final-judge').glob('*/judgment.json')))
            schedule.advance(ROOT,output,lambda *a:self.fail('Completed arms must not rerun'),judges=clients)
            self.assertEqual((Judge.calls,SonnetFixture.calls),(2,2))

    def test_failed_judge_keeps_current_generation_and_blocks_next_topic(self):
        topic=self.spec();second={**topic,'id':'second'};output=self.root/'failed';self.prepare(output)
        calls=[]
        def execute(t,arm):
            calls.append((t['id'],arm));return self.receipt(t,arm)
        original=schedule.cache_judgment
        def judge(*args,**kwargs):
            if kwargs['name']=='sonnet-5.5high':raise RuntimeError('Fixture invalid result')
            return original(*args,**kwargs)
        with patch.object(schedule,'verify_batch',return_value={'topics':[topic,second],'profile_sha256':'fixture'}),patch.object(schedule,'cache_judgment',side_effect=judge):
            with self.assertRaises(RuntimeError):schedule.advance(ROOT,output,execute,
                judges={'glm5.3flash':Judge(),'sonnet-5.5high':SonnetFixture()},poll_seconds=.001)
        self.assertEqual(calls,[('first',arm) for arm in schedule.ARMS])
        self.assertEqual(load(output/'checkpoint.json')['status'],'blocked')
        self.assertFalse((output/'topics/second').exists())
        self.assertEqual(len(list((output/'final-judge').glob('*/judgment.json'))),1)

    def test_provider_slots_serialize_distinct_candidates(self):
        output=self.root/'slots';topic=self.spec();active={n:0 for n in schedule.JUDGES};peak={n:0 for n in schedule.JUDGES}
        guard=threading.Lock();release=threading.Event()
        def fake(*args,**kwargs):
            name=kwargs['name']
            with guard:active[name]+=1;peak[name]=max(peak[name],active[name])
            release.wait(.03)
            with guard:active[name]-=1
            return {'key':'fixture'}
        positions={'direct':{'sha256':'a'},'full_first':{'sha256':'b'},'full_final':{'sha256':'a'},'none_first':{'sha256':'c'},'none_final':{'sha256':'c'}}
        with patch.object(schedule,'eligible',return_value=positions),patch.object(schedule,'cache_judgment',side_effect=fake) as mocked:
            scorer=schedule.Scoring(ROOT,output)
            try:
                scorer.submit_available(topic);result=scorer.results(topic)
            finally:scorer.close()
        self.assertEqual(peak,{n:1 for n in schedule.JUDGES})
        self.assertEqual(mocked.call_count,6)
        self.assertEqual(result['glm5.3flash']['direct'],result['glm5.3flash']['full_final'])

    def test_legacy_retirement_requires_confirmed_stop_and_no_active_job(self):
        output=self.root/'retire';topic=self.spec();self.prepare(output)
        proc=self.root/'proc';parent=proc/'1';worker=proc/'2'
        parent.mkdir(parents=True);worker.mkdir()
        (parent/'cmdline').write_bytes(b'python\0/root/lha-runtime/creative-20261101/run_batch.py\0')
        (parent/'status').write_text('State:\tT (stopped)\n')
        (worker/'status').write_text('State:\tS (sleeping)\n')
        (worker/'wchan').write_text('anon_pipe_write')
        save(output/'workers/0/tasks/first__full/run/state.json',{'status':'complete'})
        save(output/'topics/first/full.json',self.receipt(topic,'full'))
        with sqlite3.connect(output/'workers/0/queue.sqlite3') as db:
            db.execute('CREATE TABLE jobs(id INTEGER,key TEXT,kind TEXT,state TEXT)')
            db.execute("INSERT INTO jobs VALUES(1,'render','tool','running')")
        signals=[]
        def send(pid,sig):
            signals.append((pid,sig))
            if sig==signal.SIGSTOP:(worker/'status').write_text('State:\tT (stopped)\n')
            elif sig==signal.SIGCONT:(worker/'status').write_text('State:\tS (sleeping)\n')
        with patch.object(schedule.os,'kill',side_effect=send),patch.object(schedule,'verify_batch',return_value={'topics':[topic],'profile_sha256':'fixture'}):
            self.assertFalse(schedule.retire_legacy(ROOT,output,1,2,proc_root=proc))
            self.assertIn((2,signal.SIGCONT),signals)
            self.assertFalse(any(sig==signal.SIGKILL for _,sig in signals))
            with sqlite3.connect(output/'workers/0/queue.sqlite3') as db:db.execute('DELETE FROM jobs')
            self.assertTrue(schedule.retire_legacy(ROOT,output,1,2,proc_root=proc))
        self.assertEqual(signals[-2:],[(2,signal.SIGKILL),(1,signal.SIGKILL)])
        self.assertTrue((output/'scheduling/legacy-retired.json').exists())


if __name__=='__main__':unittest.main()
