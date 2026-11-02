"""Host-local atomic topic claims and one warm renderer owner per GPU.

The SQLite queue is local to one host. Multi-host workers use explicit disjoint
shards of the same plan, separate local queues, then import their signed results.
"""
import json,os,socket,sqlite3,subprocess,sys,time,uuid
from pathlib import Path
from planner_harness.common import load,save
from planner_harness.execution import immutable,signature
from planner_harness.lock import RunLock


def devices(host, *, query=None):
    import re
    selected=host.get('devices','auto')
    visible=os.environ.get('CUDA_VISIBLE_DEVICES')
    if visible is not None and visible.strip() in {'','-1'}:
        raise ValueError('Host CUDA_VISIBLE_DEVICES masks all GPUs; no dispatch')
    if host.get('renders_per_device',1)!=1:
        raise ValueError('Only one render per device is validated; provision more GPUs rather than unmeasured VRAM overcommit')
    if selected!='auto' and (not isinstance(selected,list) or not selected or any(not isinstance(d,(int,str)) or not re.fullmatch(r'[A-Za-z0-9_-]+',str(d)) for d in selected)):
        raise ValueError('devices must be auto or a nonempty safe physical index/UUID list')
    query=query or (lambda:subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid','--format=csv,noheader'],text=True))
    identities=[tuple(x.strip() for x in r.split(',')) for r in query().splitlines() if r.strip()]
    if not identities or any(len(row)!=2 for row in identities):raise ValueError('GPU inventory is unavailable or malformed')
    mapping={alias:index for index,uuid in identities for alias in (index,uuid)}
    physical={i for i,u in identities}
    allowed=[mapping.get(token.strip(),token.strip()) for token in visible.split(',')] if visible is not None else [i for i,u in identities]
    if selected=='auto':selected=allowed
    else:selected=[mapping.get(str(d),str(d)) for d in selected]
    if not set(selected)<=physical:raise ValueError('Requested GPU is absent from the host inventory')
    if not set(selected)<=set(allowed):raise ValueError('Requested GPU is masked by host CUDA_VISIBLE_DEVICES')
    if not isinstance(selected,list) or not selected or any(not isinstance(d,(int,str)) or not re.fullmatch(r'[A-Za-z0-9_-]+',str(d)) for d in selected):
        raise ValueError('devices must be auto or a nonempty safe physical index/UUID list')
    selected=[str(d) for d in selected]
    if len(set(selected))!=len(selected):raise ValueError('Duplicate GPU device')
    return selected


def shard_topics(batch,host):
    rank,count=host.get('shard_rank',0),host.get('shard_count',1)
    if type(rank)is not int or type(count)is not int or count<1 or not 0<=rank<count:raise ValueError('Use 0 <= shard_rank < shard_count')
    return [t for i,t in enumerate(batch['topics']) if i%count==rank]


def work_units(batch,host):
    """An ordered no-knowledge training chain plus independently schedulable baselines."""
    from .unified_benchmark import training_topic
    units=[];previous=None
    for topic in shard_topics(batch,host):
        methods=topic.get('methods',batch['arms'])
        if training_topic(topic,batch):
            training_method='none' if 'none' in methods else 'full'
            if host.get('shard_count',1)!=1:raise ValueError('One ordered training stream cannot be split across hosts; shard read-only test/baselines instead')
            identity=topic['id']+'__training_'+training_method
            units.append({**topic,'claim_id':identity,'methods':[training_method],'dependency':previous});previous=identity
            baseline=[m for m in methods if m!=training_method]
            if baseline:units.append({**topic,'claim_id':topic['id']+'__baselines','methods':baseline})
        else:units.append(topic)
    if previous:
        units=[{**unit,'dependency':previous} if unit.get('split') in {'validation','test'} else unit for unit in units]
    return units


def training_maintenance_settled(output,topic):
    from .unified_benchmark import training_completion
    return training_completion(output,topic['id'])['status'] not in {'pending','execution_unknown'}


class Claims:
    def __init__(self,path,topics,plan,owner):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self.owner=owner
        self.topics={t.get('claim_id',t['id']):t for t in topics}
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, ordinal INTEGER, plan TEXT, status TEXT, owner TEXT, dependency TEXT)')
            if 'dependency' not in [r[1] for r in db.execute('PRAGMA table_info(tasks)')]:db.execute('ALTER TABLE tasks ADD COLUMN dependency TEXT')
            for i,t in enumerate(topics):db.execute('INSERT OR IGNORE INTO tasks VALUES (?,?,?,"pending",NULL,?)',(t.get('claim_id',t['id']),i,plan,t.get('dependency')))
            rows=db.execute('SELECT id,plan FROM tasks').fetchall()
            if {r[0] for r in rows}!=set(self.topics) or any(r[1]!=plan for r in rows):raise ValueError('Queue differs from frozen local shard')
    def connect(self):return sqlite3.connect(self.path,timeout=30)
    def next(self,*,wait=False):
        while True:
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                row=db.execute("SELECT t.id FROM tasks t LEFT JOIN tasks p ON t.dependency=p.id WHERE t.status='pending' AND (t.dependency IS NULL OR p.status IN ('settled','topic_quarantined','settled_from_receipts')) ORDER BY t.ordinal LIMIT 1").fetchone()
                if row:
                    db.execute('UPDATE tasks SET status="claimed",owner=? WHERE id=?',(self.owner,row[0]))
                    return self.topics[row[0]]
                progressing=db.execute("SELECT EXISTS(SELECT 1 FROM tasks WHERE status='claimed') AND EXISTS(SELECT 1 FROM tasks WHERE status='pending')").fetchone()[0]
            if not wait or not progressing:return None
            time.sleep(.1)

    def finish(self,identity,status):
        with self.connect() as db:
            cursor=db.execute('UPDATE tasks SET status=? WHERE id=? AND owner=? AND status="claimed"',(status,identity,self.owner))
            if cursor.rowcount!=1:raise ValueError('Task claim belongs to a different worker')
    def recover(self,output):
        from .unified_benchmark import training_topic
        """Completed receipts recover claims. Dead unsubmitted claims can requeue.

        A submitted render/model without a method settlement stays quarantined;
        process death alone never proves that external work stopped.
        """
        from planner_harness.owned_process import birth
        output=Path(output)
        ledger=load(output/'accounting/ledger.json') if (output/'accounting/ledger.json').exists() else {}
        batch=load(output/'batch.json')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            for identity,owner in db.execute('SELECT id,owner FROM tasks WHERE status="claimed"').fetchall():
                parts=owner.split(':')
                alive=parts[0]==socket.gethostname() and birth(int(parts[1]))==parts[2]
                if alive:continue
                topic=self.topics[identity]
                receipts=[output/'methods'/topic['id']/m/'settlement.json' for m in topic.get('methods',batch['arms'])]
                if all(p.exists() and load(p).get('batch_sha256')==batch['sha256'] for p in receipts):
                    outcomes={load(p).get('status') for p in receipts}
                    needs_maintenance=training_topic(topic,batch) and not training_maintenance_settled(output,topic)
                    status='recovery_required' if outcomes & {'execution_unknown','topic_quarantined','unexecuted'} else 'pending' if needs_maintenance else 'settled_from_receipts'
                else:
                    operations=[r for r in ledger.get('operations',{}).values() if r['topic']==topic['id'] and r.get('lane') in topic.get('methods',batch['arms']) and r['status']!='not_submitted']
                    # Even successful external calls without their final method
                    # receipt need original task recovery, never a fresh claim.
                    status='recovery_required' if operations else 'pending'
                db.execute('UPDATE tasks SET status=?,owner=NULL WHERE id=?',(status,identity))

    def rows(self):
        with self.connect() as db:return [dict(zip(('topic','status','owner'),r)) for r in db.execute('SELECT id,status,owner FROM tasks ORDER BY ordinal')]


def worker(root,output,host,device):
    from .unified_benchmark import verify,run_serial
    output=Path(output);batch=verify(root,output)
    from planner_harness.owned_process import birth
    identity=socket.gethostname()+':'+str(os.getpid())+':'+str(birth(os.getpid()))+':'+str(device)+':'+uuid.uuid4().hex
    queue=Claims(output/'device-queue.sqlite3',work_units(batch,host),batch['sha256'],identity)
    single={**host,'devices':[device]}
    try:
        return run_serial(root,output,single,claim=queue)
    finally:
        # Claimed work is retained unknown on crash. No lease timeout authorizes
        # duplicate generation; recovery inspects that original task receipt.
        save(output/'workers'/str(device)/'dispatch-owner.json',{'owner':identity,'claims':queue.rows()})


def dispatch_status(positions,claims):
    unresolved={'execution_unknown','unexecuted','topic_quarantined','recovery_required','gpu_quarantined','pending','claimed'}
    return 'partial' if any(r['status'] in unresolved for r in [*positions,*claims]) else 'settled'


def run_devices(root,output,host):
    from .unified_benchmark import verify,preflight,policy
    from planner_harness import accounting
    from . import results
    root,output=Path(root).resolve(),Path(output).resolve();batch=verify(root,output)
    selected=devices(host);topics=shard_topics(batch,host)
    frozen_host={**host,'devices':selected,'budget':policy(batch,host.get('budget'))}
    if host.get('local_results_root'):
        frozen_host['local_results_root']=str(Path(host['local_results_root']).resolve())
    ensure_local_queue(output)
    with scheduler_owner(output):
        immutable(output/'host.json',frozen_host)
        accounting.install(output/'accounting',frozen_host['budget'],require_live=True)
        if host.get('local_results_root'):
            batch={**batch,'results_root':str(Path(host['local_results_root']).resolve())}
            results.register_plan(batch['results_root'],batch)
        preflight(root,output,frozen_host)
        immutable(output/'dispatch-plan.json',{'batch_sha256':batch['sha256'],'host':socket.gethostname(),
            'devices':selected,'renders_per_device':1,'shard_rank':host.get('shard_rank',0),'shard_count':host.get('shard_count',1),
            'topics':[t['id'] for t in topics],'coordination':'host-local SQLite; disjoint explicit shards across hosts'})
        queue=Claims(output/'device-queue.sqlite3',work_units(batch,host),batch['sha256'],'supervisor')
        queue.recover(output)
        children=[];recovered=set()
        try:
            for device in selected:
                directory=output/'workers'/device;directory.mkdir(parents=True,exist_ok=True)
                stream=(directory/'dispatch.log').open('ab')
                command=[sys.executable,'-B',str(root/'scripts/benchmark_device_worker.py'),'--root',str(root),'--output',str(output),'--host-config',str(output/'host.json'),'--device',device,'--scheduler-pid',str(os.getpid()),'--scheduler-birth',str(__import__('planner_harness.owned_process',fromlist=['birth']).birth(os.getpid()))]
                child=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
                from planner_harness.owned_process import birth
                children.append((child,stream,device,birth(child.pid)))
            while any(child.poll() is None for child,_,_,_ in children):
                for child,_,device,_ in children:
                    if child.poll() is not None and device not in recovered:
                        queue.recover(output);recovered.add(device)
                save(output/'dispatch-status.json',{'claims':queue.rows(),'workers':{d:c.poll() for c,_,d,_ in children}})
                time.sleep(1)
        finally:
            stop_children(children,output)
        positions=[]
        for topic in topics:
            for method in topic.get('methods',batch['arms']):
                path=output/'methods'/topic['id']/method/'settlement.json'
                positions.append(load(path) if path.exists() else {'topic':topic['id'],'method':method,'batch_sha256':batch['sha256'],
                    'status':'unexecuted','reason':'No completed method receipt; inspect original device claim before recovery'})
        result={'status':dispatch_status(positions,queue.rows()),
            'topics':topics,'positions':positions,'workers':{d:c.returncode for c,_,d,_ in children},'claims':queue.rows(),
            'quality_scoring':'pending_new_evaluation'}
        save(output/'checkpoint.json',result);results.report(root,batch['results_root'])
        # Training maintenance is ordered per none task; validation/test are read-only.
        return result


def stop_children(children,output):
    """Signal only our recorded worker identities; workers cancel their own requests."""
    import signal
    from planner_harness.owned_process import birth
    receipts=[]
    for child,stream,device,identity in children:
        if child.poll() is None and identity is not None and birth(child.pid)==identity:
            os.kill(child.pid,signal.SIGTERM)
    deadline=time.monotonic()+10
    for child,stream,device,identity in children:
        if child.poll() is None:
            try:child.wait(timeout=max(0,deadline-time.monotonic()))
            except subprocess.TimeoutExpired:pass
        receipts.append({'device':device,'pid':child.pid,'birth':identity,'worker_stopped':child.poll() is not None,
                         'resource_release':'See per-task cancellation receipts; worker exit alone is not release proof'})
        stream.close()
    save(Path(output)/'dispatch-stop.json',{'workers':receipts})


from contextlib import contextmanager
@contextmanager
def scheduler_owner(output):
    import signal
    def stop(signum,frame):raise KeyboardInterrupt('Owning scheduler received stop')
    previous=signal.signal(signal.SIGTERM,stop)
    try:
        with RunLock(Path(output)/'unified-owner'):yield
    finally:signal.signal(signal.SIGTERM,previous)


def ensure_local_queue(output):
    """Refuse known network filesystems; cross-host operation uses disjoint shards."""
    output=Path(output).resolve();mounts=Path('/proc/self/mountinfo')
    if not mounts.exists():raise ValueError('Host-local queue requires Linux mount identity')
    matching=[]
    for line in mounts.read_text().splitlines():
        before,after=line.split(' - ',1);point=before.split()[4].replace('\\040',' ')
        if output.is_relative_to(point):matching.append((len(point),after.split()[0]))
    filesystem=max(matching)[1] if matching else None
    if filesystem in {'nfs','nfs4','cifs','smb3','9p','fuse.sshfs'}:
        raise ValueError('Device queue must be on a host-local filesystem; use disjoint local shards and import results across hosts')
