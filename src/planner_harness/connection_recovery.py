"""Reclassify proven local connection refusals without changing original receipts."""
from pathlib import Path
from urllib.parse import urlsplit

from .common import load, sha
from .execution import immutable


def refused_before_request(audit):
    if (audit.get('backend') != 'chatgpt_subscription'
            or urlsplit(audit.get('endpoint','')).hostname not in {'localhost','127.0.0.1','::1'}
            or audit.get('stage') != 'connect' or not audit.get('finished_unix')
            or audit.get('received_bytes') != 0 or audit.get('event_count') != 0
            or any(audit.get(k) for k in ('http_status','response_id','terminal_event','relay_error'))):
        return False
    error = audit.get('error') or {}
    return ((error.get('type') == 'ConnectionRefusedError' and error.get('errno') in {61,111,10061})
            or (error.get('type') == 'URLError' and error.get('message') in {
                '<urlopen error [Errno 111] Connection refused>',
                '<urlopen error [Errno 61] Connection refused>'}))


def reconcile(binding, key):
    from . import accounting as a
    record = a.operation(binding,key)
    if not record or record['kind'] != 'model' or record['status'] == 'not_submitted':
        return False
    entry = Path(key)
    audit_path,stream,unknown = entry/'client-audit/summary.json',entry/'client-audit/stream.bin',entry/'unknown.json'
    if not all(p.is_file() for p in (audit_path,stream,unknown)) or (entry/'response.txt').exists():
        return False
    audit = load(audit_path)
    if not refused_before_request(audit) or stream.stat().st_size:
        return False
    if audit.get('stream_sha256') and audit['stream_sha256'] != sha(stream):
        return False
    saved_unknown = load(unknown)
    if not audit.get('request_id') or (saved_unknown.get('client_execution') or {}).get('request_id') != audit['request_id']:
        return False
    if saved_unknown.get('scope') != binding:
        return False
    completion = record.get('completion')
    if not completion or sha(completion['path']) != completion['sha256']:
        return False
    value = load(completion['path'])
    if value.get('status') != 'failed' or value.get('usage'):
        return False
    from .lock import RunLock
    from .execution import signature
    directory = Path(binding['root'])/'operations'/signature({'id':key})
    with RunLock(directory/'execution-owner'):
        record = a.operation(binding,key)
        if record['status'] == 'not_submitted':return False
        proof = entry/'connection-refusal.json'
        immutable(proof,{'reason':'Local TCP connection refused before the request was accepted',
                         'audit':{'path':str(audit_path),'sha256':sha(audit_path)},
                         'unknown_sha256':sha(unknown),'original_operation':record})
        a.transition(binding,key,'not_submitted',charged_tokens=0,charged_amount='0',
                     settled_amount='0',actual_usage={},cost_status='connection_refused_before_request',
                     reconciliation={'path':str(proof),'sha256':sha(proof)})
    return True
