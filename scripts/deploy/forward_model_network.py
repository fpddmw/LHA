"""Temporary loopback-only SSH route for HTTPS model traffic on the owned server.

TLS remains end-to-end. This forwards CONNECT streams for OpenAI domains only;
it does not inspect prompts, tokens or credentials and does not listen publicly.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import select
import socket
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts/deploy')]
from planner_harness.lock import RunLock

p=argparse.ArgumentParser()
p.add_argument('--private-config',type=Path,required=True)
p.add_argument('--dependencies',type=Path,required=True)
p.add_argument('--state',type=Path,required=True)
p.add_argument('--port',type=int,default=17891)
p.add_argument('--host-fingerprint', help='Verified SSH SHA256 fingerprint (base64), for another authorized host')
p.add_argument('--owner-name', default='model-network-route-owner', help='Distinct lock for a separately authorized host')
a=p.parse_args()
sys.path.insert(0,str(a.dependencies))
import control_bernini_loop
import paramiko

def relay(channel):
    target=None
    try:
        header=b''
        while b'\r\n\r\n' not in header:
            block=channel.recv(4096)
            if not block:return
            header+=block
            if len(header)>8192:raise ValueError('Proxy header too large')
        method,authority,_=header.split(b'\r\n',1)[0].decode('ascii').split(' ',2)
        host,separator,port=authority.rpartition(':')
        allowed=host in {'chatgpt.com','openai.com'} or host.endswith(('.chatgpt.com','.openai.com'))
        if method!='CONNECT' or separator!=':' or port!='443' or not re.fullmatch(r'[A-Za-z0-9.-]+',host) or not allowed:
            channel.sendall(b'HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n');return
        target=socket.create_connection((host,443),timeout=30)
        channel.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')
        remainder=header.split(b'\r\n\r\n',1)[1]
        if remainder:target.sendall(remainder)
        while True:
            readable,_,_=select.select([target,channel],[],[],60)
            for incoming in readable:
                content=incoming.recv(65536)
                if not content:return
                (channel if incoming is target else target).sendall(content)
    except (OSError,ValueError,EOFError):
        # Never print headers or traffic. Endpoint failures are returned to the caller.
        pass
    finally:
        if target:target.close()
        channel.close()

def accept(channel,origin,server):
    threading.Thread(target=relay,args=(channel,),daemon=True).start()

history=[]

def record(status,**fields):
    event={'status':status,'at':datetime.now(timezone.utc).isoformat(),**fields}
    history.append(event)
    temporary=a.state.with_suffix('.part')
    temporary.write_text(json.dumps({**event,'pid':os.getpid(),
        'remote_bind':'127.0.0.1','port':a.port,'destination_scope':'OpenAI HTTPS only',
        'local_network_required':True,'history':history[-40:]},indent=2)+'\n',encoding='utf-8')
    temporary.replace(a.state)

if not re.fullmatch(r'[A-Za-z0-9_-]+',a.owner_name):
    raise ValueError('Owner name must be a safe basename')
with RunLock(a.state.parent/a.owner_name):
    control_bernini_loop.configure_renderer('bernini')
    if a.host_fingerprint:
        control_bernini_loop.HOST_FINGERPRINT=a.host_fingerprint.removeprefix('SHA256:').rstrip('=')+'='
    failures=0
    while True:
        connection=None
        connected_at=None
        try:
            connection=control_bernini_loop.connect(a.private_config)
            transport=connection.get_transport()
            transport.set_keepalive(30)
            transport.request_port_forward('127.0.0.1',a.port,handler=accept)
            connected_at=time.monotonic()
            record('active')
            print('Loopback-only model network route active.',flush=True)
            while transport.is_active():
                # A round trip also detects a dead connection during long GPU work.
                _,stdout,_=connection.exec_command('true',timeout=15)
                stdout.read()
                if stdout.channel.recv_exit_status()!=0:
                    raise OSError('SSH liveness command failed')
                time.sleep(30)
            raise EOFError('SSH transport closed')
        except (paramiko.AuthenticationException,paramiko.BadHostKeyException,RuntimeError) as exc:
            # Authentication and pinned-identity failures require inspection.
            record('failed',error_type=type(exc).__name__)
            raise
        except (OSError,EOFError,paramiko.SSHException) as exc:
            if connected_at and time.monotonic()-connected_at>=300:
                failures=0
            failures+=1
            if failures>=12:
                record('failed',error_type=type(exc).__name__,consecutive_failures=failures)
                raise
            delay=min(60,5*2**min(failures-1,4))
            record('reconnecting',error_type=type(exc).__name__,retry_seconds=delay,
                   consecutive_failures=failures)
        finally:
            if connection:connection.close()
        # Reconnect transport only. Never replay a model request or its bytes.
        time.sleep(delay)
