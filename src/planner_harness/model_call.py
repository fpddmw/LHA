"""Durable text response with bounded, recorded transport retries; no semantic retries."""
from __future__ import annotations

import copy
import os
from pathlib import Path
import time

from .common import load, save, sha, stamp
from .execution import immutable
from .lock import RunLock
from .integrity import IntegrityError
from .resources import ResourceExhausted
from .accounting import BudgetConfigurationError


class ModelTransportError(RuntimeError):
    def __init__(self, message, *, retryable=True, provider_error=None):
        super().__init__(message)
        self.retryable = retryable
        self.failure_kind = "model_transport"
        self.provider_error=provider_error
        self.http_status=(provider_error or {}).get("status")


class ProviderDispatchPaused(ModelTransportError):
    def __init__(self,provider_error):
        super().__init__('Provider dispatch paused until external quota/balance is restored',retryable=False,provider_error=provider_error)
        self.failure_kind='provider_dispatch_paused'
        self.recoverable_after_external_change=True


def reopen_call(directory, reason, extra_attempts=1):
    """Operator recovery of the same request; no inference or semantic retry."""
    directory = Path(directory)
    if not reason.strip() or type(extra_attempts) is not int or not 1 <= extra_attempts <= 3:
        raise ValueError("Record a recovery reason and one to three additional transport attempts")
    with RunLock(directory):
        if not (directory / "input.json").exists():
            raise ValueError("There is no submitted immutable call to recover")
        if (directory / "response.txt").exists() or list((directory / "attempts").glob("*/response.txt")):
            raise ValueError("A response already exists; valid or invalid answers cannot be reinterpreted")
        attempts = [p for p in (directory / "attempts").glob("*") if p.is_dir() and p.name.isdigit()]
        if not attempts:
            raise ValueError("No transport attempt has been recorded")
        if any((p/"unknown.json").exists() or ((p/"submitted.json").exists() and not (p/"failed.json").exists()) for p in attempts):
            raise ValueError("Reconcile the original unknown execution with evidence before authorizing any new submission")
        last = max(int(p.name) for p in attempts)
        policy = {"first": last + 1, "last": last + extra_attempts}
        history = directory / "recoveries"
        entry = history / f"{len(list(history.glob('*.json'))) + 1:04d}.json"
        immutable(entry, {"at": stamp(), "reason": reason, "input_sha256": sha(directory / "input.json"),
                          "previous": load(directory / "allowance.json") if (directory / "allowance.json").exists() else None,
                          "next": policy, "note": "Interrupted provider calls may have incurred cost; previous attempts are retained."})
        save(directory / "allowance.json", policy)
        return policy


def write_text_atomic(path, text):
    from .common import write_atomic
    write_atomic(path, text)


def transient(exc):
    if getattr(exc, "retryable", None) is not None:
        return bool(exc.retryable)
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    text = str(exc).lower()
    if any(x in text for x in ("unauthorized", "forbidden", "quota", "invalid_api_key", "unsupported")):
        return False
    return any(x in text for x in ("timed out", "timeout", "connection reset", "connection error",
                                   "stream disconnected", "unexpected eof", "502", "503", "504", "429",
                                   "workspace routing discovery failed", "error sending request", "rate limit"))


def returned_receipt(directory, *, recovered=True):
    """Repair a crash after durable text, using only its original attempt record."""
    directory = Path(directory)
    raw = directory / "response.txt"
    matches = [p for p in (directory / "attempts").glob("*/response.txt") if sha(p) == sha(raw)]
    if not matches:
        raise IntegrityError("Saved response has no matching durable transport attempt")
    attempt = min(matches, key=lambda p: int(p.parent.name)).parent
    result_path = attempt / "result.json"
    result = load(result_path) if result_path.exists() else {"usage": {}, "metadata_status": "legacy_unknown"}
    receipt = {"attempt": int(attempt.name), "sha256": sha(raw),
               "usage": result.get("usage", {}), "finish_reason": result.get("finish_reason"),
               "output_budget": result.get("output_budget"), "result_path": str(result_path)}
    target = directory / "returned.json"
    if target.exists():
        old = load(target)
        if old.get("sha256") != receipt["sha256"] or old.get("attempt") != receipt["attempt"]:
            raise IntegrityError("Returned model receipt differs from the durable answer")
        return old
    save(target, {**receipt, "at": stamp(), "recovered": recovered})
    return load(target)


def collect_owned_answer(directory, entry, accounting_scope, output_budget, capabilities):
    """Recover only the original durable late response, without provider dispatch."""
    from .accounting import operation, ExternalExecutionUnknown
    record = operation(accounting_scope, str(entry.resolve()))
    if not record or not record.get("completion"):
        raise ExternalExecutionUnknown("Original model execution has no durable late completion yet")
    completion = record["completion"]
    if sha(completion["path"]) != completion["sha256"]:
        raise IntegrityError("Original model completion receipt changed")
    saved = load(completion["path"])
    if saved.get("status") != "complete" or not isinstance(saved.get("result", {}).get("text"), str):
        raise ExternalExecutionUnknown("Original model execution has no successful recoverable answer")
    value = saved["result"]
    save(entry / "result.json", {"usage": value.get("usage", saved.get("usage", {})),
        "finish_reason": value.get("finish_reason"), "output_budget": output_budget,
        "budget_capabilities": capabilities, "collected_original_completion": completion,
        "output_limit": {"requested_tokens": output_budget, "hard_enforced": bool(capabilities.get("hard_output_tokens"))}})
    write_text_atomic(entry / "response.txt", value["text"])
    write_text_atomic(directory / "response.txt", value["text"])
    returned_receipt(directory, recovered=True)
    return value["text"]


def _wait_for_provider_retry(scope, previous_attempt):
    from .accounting import check_task, load_ledger, online_limits
    from .resources import TaskDeadline

    failure = previous_attempt / "failed.json"
    if not failure.exists():
        return
    wait = load(failure).get("retry_not_before_unix", 0) - time.time()
    if wait <= 0:
        return
    if online_limits(scope):
        check_task(scope)
        clock = load_ledger(scope["root"])["topics"][scope["topic"]]["lanes"][scope["lane"]]
        if clock["deadline_unix"] is not None and time.time() + wait >= clock["deadline_unix"]:
            raise TaskDeadline("Provider retry-after exceeds the original task deadline")
    time.sleep(wait)
    check_task(scope)


def call_text(directory, model, system, user, images, *, attempts=3, retry_delay=2, max_new_tokens=7000, meter_only=False):
    if meter_only:return metered_text(directory,model,system,user,images,max_new_tokens=max_new_tokens)
    directory = Path(directory)
    with RunLock(directory):
        binding = {"system_prompt": system, "user_text": user,
                   "images": [{"path": str(p), "sha256": sha(p)} for p in images],
                   "model": model.model, "reasoning_effort": getattr(model, "reasoning_effort", None)}
        runtime_identity = getattr(model, "runtime_identity", None)
        if callable(runtime_identity):
            binding["transport"] = runtime_identity()
        try:
            immutable(directory / "input.json", binding)
        except ValueError as exc:
            raise IntegrityError(str(exc)) from None
        raw_path = directory / "response.txt"
        if raw_path.exists():
            returned_receipt(directory)
            return raw_path.read_text(encoding="utf-8")
        policy_path = directory / "allowance.json"
        if not policy_path.exists():
            immutable(policy_path, {"first": 1, "last": attempts})
        policy = load(policy_path)
        from .accounting import discover, invoke, ExternalExecutionUnknown
        accounting_scope = discover(directory,model)
        from .accounting import check_model_capabilities
        capabilities = check_model_capabilities(accounting_scope, model)
        # Clone only transport controls. Never change the shared model instance.
        client = copy.copy(model)
        client.lha_accounting_scope = accounting_scope
        for key in ("attempts", "max_retries"):
            if hasattr(client, key):
                setattr(client, key, 1 if key == "attempts" else 0)
        for number in range(policy["first"], policy["last"] + 1):
            entry = directory / "attempts" / f"{number:02d}"
            if (entry / "response.txt").exists():
                raw = (entry / "response.txt").read_text(encoding="utf-8")
                write_text_atomic(raw_path, raw)
                returned_receipt(directory)
                return raw
            if (entry / "failed.json").exists():
                failed = load(entry / "failed.json")
                if failed.get("failure_kind") == "integrity_error":
                    raise IntegrityError("Recorded model identity/response integrity failure")
                if not failed["retryable"]:
                    raise ModelTransportError("Recorded permanent model failure; explicit recovery is required", retryable=False)
                continue
            if (entry / 'submitted.json').exists():
                from .accounting import operation,reserve as reserve_unified,transition
                if operation(accounting_scope,str(entry.resolve())) is None:
                    target = 'model:'+model.model+'/'+str(getattr(model,'reasoning_effort',None) or 'none')
                    reserve_unified(accounting_scope,str(entry.resolve()),'model',target,(len(system)+len(user))//3+len(images)*1600+max_new_tokens)
                    transition(accounting_scope,str(entry.resolve()),'in_flight_unknown',origin='imported_prior_submission')
                    save(entry/'unknown.json',{'failure_kind':'external_execution_unknown','scope':accounting_scope})
            if (entry / "unknown.json").exists():
                return collect_owned_answer(directory, entry, accounting_scope, max_new_tokens, capabilities)
            _wait_for_provider_retry(accounting_scope, entry.parent / f"{number - 1:02d}")
            budget = getattr(model, "lha_resource_budget", None)
            if budget and budget["policy"].get("max_cost") is not None:
                from .resources import reserve, check_wall
                state_file = Path(budget["root"]) / "state.json"
                if state_file.exists():
                    check_wall(load(state_file))
                estimate = (len(system) + len(user)) // 3 + len(images) * 1600 + max_new_tokens
                reserve(budget["root"], entry, budget["policy"], estimate)
            try:
                def submit():
                    save(entry / "submitted.json", {"at":stamp(),"logical_call":str(directory),"attempt":number})
                def request():
                    client.lha_audit_directory = str(entry / "client-audit")
                    client.last_usage = {}
                    client.last_provider_response = {}
                    client.last_finish_reason = None
                    client.last_provider_model = None
                    value = client.predict_text(system_prompt=system,user_text=user,image_paths=images,max_new_tokens=max_new_tokens)
                    body = getattr(client,'last_provider_response',{})
                    finish = getattr(client,'last_finish_reason',None)
                    if not finish and isinstance(body,dict):
                        finish = body.get('stop_reason') or (body.get('choices') or [{}])[0].get('finish_reason')
                    return {'text':value,'usage':getattr(client,'last_usage',{}),'finish_reason':finish}
                target = "model:"+model.model+"/"+str(getattr(model,"reasoning_effort",None) or "none")
                accounted = invoke(accounting_scope,str(entry.resolve()),"model",target,request,
                    tokens=(len(system)+len(user))//3+len(images)*1600+max_new_tokens,
                    before_submit=submit,usage_getter=lambda:getattr(client,"last_usage",{}),owner=getattr(client,"lha_service_owner",None))
                raw = accounted["text"]
                client.last_usage = accounted["usage"]
                client.last_finish_reason = accounted["finish_reason"]
                if not isinstance(raw, str):
                    raise ValueError("Model did not return text")
            except ExternalExecutionUnknown as exc:
                save(entry / "unknown.json", {"failure_kind":exc.failure_kind,"at":stamp(),"scope":accounting_scope,"client_execution":getattr(client,"last_client_audit",None)})
                raise
            except ResourceExhausted:
                raise
            except BudgetConfigurationError:
                raise
            except IntegrityError:
                save(entry / "failed.json", {"type":"IntegrityError", "failure_kind":"integrity_error", "retryable":False})
                raise
            except Exception as exc:
                if getattr(model,"requires_live_budget",False) and isinstance(exc,(TimeoutError,ConnectionError)):
                    save(entry / "unknown.json", {"failure_kind":"external_execution_unknown","at":stamp(),"scope":accounting_scope})
                    raise ExternalExecutionUnknown("Provider timeout retains unknown execution/cost; reconcile before resubmission") from None
                retryable = False if getattr(exc,"retryable",None) is False else transient(exc)
                # Do not persist provider error bodies that can contain credentials.
                diagnostic = getattr(exc, "safe_diagnostic", None)
                failure = {"type": type(exc).__name__, "retryable": retryable, "failure_kind": getattr(exc, "failure_kind", None),
                           "client_execution": getattr(client, "last_client_audit", None), "provider_error": diagnostic}
                retry_after = getattr(exc, "retry_after", None)
                if retryable and retry_after is not None:
                    failure["retry_not_before_unix"] = time.time() + retry_after
                save(entry / "failed.json", failure)
                if not retryable or number == policy["last"]:
                    raise ModelTransportError("Model transport failed; inspect recorded attempt status", retryable=retryable,provider_error=diagnostic) from None
                if retry_after is None:
                    time.sleep(retry_delay * number)
                continue
            body = getattr(client, "last_provider_response", {})
            finish = getattr(client, "last_finish_reason", None)
            if not finish and isinstance(body, dict):
                finish = body.get("stop_reason") or (body.get("choices") or [{}])[0].get("finish_reason")
            save(entry / "result.json", {"usage": getattr(client, "last_usage", {}),
                 "finish_reason": finish, "output_budget": max_new_tokens,
                 "output_limit": getattr(client, "last_output_limit", {"requested_tokens": max_new_tokens,
                     "hard_enforced": bool(capabilities.get("hard_output_tokens"))}),
                 "budget_capabilities": capabilities,"client_execution":getattr(client,"last_client_audit",None)})
            if budget and budget["policy"].get("max_cost") is not None:
                from .resources import reconcile
                reconcile(budget["root"], entry, getattr(client, "last_usage", {}))
            write_text_atomic(entry / "response.txt", raw)
            write_text_atomic(raw_path, raw)
            returned_receipt(directory, recovered=False)
            return raw
        raise ModelTransportError("Recorded transport retry budget exhausted; explicitly reopen the same call")


def metered_text(directory,model,system,user,images,*,max_new_tokens=None):
    """Independent final transport: true usage receipts, no quota admission.

    The provider's request timeout still applies. An interrupted request remains
    unknown and cannot be blindly repeated. Report recovery owns finite retries.
    """
    from .accounting import ExternalExecutionUnknown
    directory=Path(directory)
    with RunLock(directory):
        binding={'system_prompt':system,'user_text':user,'images':[{'path':str(p),'sha256':sha(p)} for p in images],
            'model':model.model,'reasoning_effort':getattr(model,'reasoning_effort',None)}
        if callable(getattr(model,'runtime_identity',None)):binding['transport']=model.runtime_identity()
        immutable(directory/'input.json',binding)
        immutable(directory/'meter-only.json',{'mode':'live_meter_only' if getattr(model,'requires_live_budget',False) else 'fixture_meter_only',
            'admission_limits':None,'output_token_reservation':None,'cost':'Unknown without provider invoice; actual usage retained'})
        allowance=directory/'allowance.json'
        if not allowance.exists():immutable(allowance,{'first':1,'last':1})
        number=load(allowance)['first']
        raw=directory/'response.txt';entry=directory/'attempts'/f'{number:02d}'
        if raw.exists():returned_receipt(directory);return raw.read_text()
        if (entry/'response.txt').exists():
            write_text_atomic(raw,(entry/'response.txt').read_text());returned_receipt(directory);return raw.read_text()
        if (entry/'submitted.json').exists() and not (entry/'failed.json').exists():
            raise ExternalExecutionUnknown('Original independent final request remains unknown; no duplicate submission')
        if (entry/'failed.json').exists():
            failed=load(entry/'failed.json')
            if failed.get('failure_kind')=='integrity_error':raise IntegrityError('Recorded provider identity failure')
            if (failed.get('provider_error') or {}).get('category') in {'provider_balance_insufficient','quota_exhausted'}:raise ProviderDispatchPaused(failed['provider_error'])
            raise ModelTransportError('Recorded independent final transport failure',retryable=failed['retryable'],provider_error=failed.get('provider_error'))
        client=copy.copy(model)
        for key,value in [('attempts',1),('max_retries',0)]:
            if hasattr(client,key):setattr(client,key,value)
        started=time.time();save(entry/'submitted.json',{'at':stamp(),'started_unix':started,'mode':'meter_only'})
        try:
            client.lha_audit_directory=str(entry/'client-audit');client.last_usage={};client.last_provider_response={};client.last_finish_reason=None
            value=client.predict_text(system_prompt=system,user_text=user,image_paths=images,max_new_tokens=max_new_tokens)
            if not isinstance(value,str):raise ValueError('Provider returned no text')
        except IntegrityError:
            save(entry/'failed.json',{'failure_kind':'integrity_error','retryable':False});raise
        except ExternalExecutionUnknown:
            save(entry/'unknown.json',{'status':'execution_unknown','mode':'meter_only','client_execution':getattr(client,'last_client_audit',None)})
            raise
        except (TimeoutError,ConnectionError) as exc:
            save(entry/'unknown.json',{'status':'execution_unknown','type':type(exc).__name__,'cost_status':'unknown','mode':'live_meter_only'})
            raise ExternalExecutionUnknown('Independent final request timed out; original execution/usage remains unknown') from None
        except Exception as exc:
            retryable=transient(exc)
            diagnostic=getattr(exc,'safe_diagnostic',None)
            save(entry/'failed.json',{'type':type(exc).__name__,'retryable':retryable,'mode':'meter_only','provider_error':diagnostic})
            if (diagnostic or {}).get('category') in {'provider_balance_insufficient','quota_exhausted'}:raise ProviderDispatchPaused(diagnostic) from None
            raise ModelTransportError('Independent final provider failure',retryable=retryable,provider_error=diagnostic) from None
        body=getattr(client,'last_provider_response',{});finish=getattr(client,'last_finish_reason',None)
        if not finish and isinstance(body,dict):finish=body.get('stop_reason') or (body.get('choices') or [{}])[0].get('finish_reason')
        save(entry/'result.json',{'usage':getattr(client,'last_usage',{}),'finish_reason':finish,'output_budget':None,
            'output_limit':getattr(client,'last_output_limit',{'requested_tokens':None,'mode':'provider_default'}),
             'client_execution':getattr(client,'last_client_audit',None),
             'accounting_mode':'live_meter_only' if getattr(model,'requires_live_budget',False) or getattr(model,'is_live_api',False) else 'fixture_meter_only',
            'elapsed_seconds':time.time()-started,'cost_status':'unknown_without_invoice'})
        write_text_atomic(entry/'response.txt',value);write_text_atomic(raw,value);returned_receipt(directory,recovered=False)
        return value
