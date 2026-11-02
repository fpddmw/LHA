"""Precommitted, score-independent recovery of report transport/format failures."""
from pathlib import Path
import copy,json

from .common import load, sha
from .execution import immutable
from .integrity import IntegrityError
from .json_output import decode_object
from .model_call import ModelTransportError, ProviderDispatchPaused, call_text

POLICY = {"version": "report-recovery-v2-capacity-and-format", "max_attempts": 2,
          "output_tokens_per_attempt": 16384, "max_reserved_output_tokens": 32768, "capacity_output_tokens": [16384,16384], "retry_feedback_max_chars":4096,
          "max_context_estimated_tokens": 200000,
          "selection": "first structurally and evidentially valid answer after the stage-specific deterministic projection",
          "retry_input":"Fixed neutral format/evidence repair feedback, prior input/response hashes; judgments are not score-targeted",
          "retry_categories": ["capacity", "json_format", "schema_or_evidence", "transport"],
          "money": "Unknown provider cost is retained as unknown; output reservation bounds calls, not exact monetary cost."}


FINAL_POLICY={**POLICY,'version':'independent-final-meter-only-v1','output_tokens_per_attempt':None,
    'max_reserved_output_tokens':None,'capacity_output_tokens':[None,None],'max_context_estimated_tokens':None,
    'admission':'No artificial token/call/cost quotas; provider request timeout and finite fault recovery only',
    'output_protocol':'GLM omits max_tokens; Native Sonnet uses documented model protocol maximum when required'}


class ReportUnavailable(ValueError):
    failure_kind = "report_unavailable"


def retry_packet(packet,failures,policy=None):
    policy=policy or POLICY
    if packet.get("input_projection") in {"online-evidence-v1","evidence-v1"}:
        from critic_harness.evidence import model_packet
        packet=model_packet(packet)
    if not failures:return packet
    result=copy.deepcopy(packet)
    feedback={'protocol':policy['version'],'instruction':'Repair only JSON structure, completeness and evidence references using the supplied IDs. Preserve substantive judgments and evidence uncertainty. No target score or preferred outcome is supplied.',
        'previous_attempts':[{'category':r['category'],'error':r['error'][:policy['retry_feedback_max_chars']],
             'input_sha256':r['input_sha256'],'response_sha256':r.get('response_sha256')} for r in failures]}
    try:visible=json.loads(result['user_text'])
    except (ValueError,TypeError):visible={'original_user_text':result['user_text']}
    if not isinstance(visible,dict):visible={'original_user_text':result['user_text']}
    visible['report_recovery']=feedback
    result['user_text']=json.dumps(visible,ensure_ascii=False,separators=(',',':'))
    return result


def output_tokens(failures,policy=None):
    policy=policy or POLICY
    return policy['capacity_output_tokens'][1] if any(r['category']=='capacity' for r in failures) else policy['output_tokens_per_attempt']


def attempt_packet(call,packet):
    call=Path(call)
    if call.parent.parent.name!='report-attempts':return retry_packet(packet,[])
    root=call.parents[2];number=int(call.parent.name);failures=[]
    for previous in range(1,number):
        prior=root/('call' if previous==1 else f'report-attempts/{previous:02d}/call')
        path=prior.parent/('report-failure.json' if previous==1 else 'failure.json')
        record=load(path)
        if record['call_path']!=str(prior) or sha(prior/'input.json')!=record['input_sha256'] or (record.get('response_sha256') and sha(prior/'response.txt')!=record['response_sha256']):
            raise IntegrityError('Previous report recovery evidence changed')
        failures.append(record)
    return retry_packet(packet,failures,load(root/'recovery-policy.json'))


def call_report(directory, model, packet, images, validate, *, usage="online_feedback"):
    policy=FINAL_POLICY if usage=="independent_final" else POLICY
    directory = Path(directory)
    immutable(directory / "recovery-policy.json", policy)
    from .working_memory import estimate
    visible_packet = retry_packet(packet, [], policy)
    context = estimate(visible_packet["system_prompt"], visible_packet["user_text"], len(images))
    context["reserve_tokens"] = (max(policy["capacity_output_tokens"]) if usage!="independent_final" else 0)+policy["retry_feedback_max_chars"]//3
    context["total_estimated"] = context["text_tokens_estimated"] + context["image_tokens_estimated"] + context["reserve_tokens"]
    context["limit"] = policy["max_context_estimated_tokens"]
    context["capacity_scope"] = "Operator submission guard; provider-specific capacity is verified by preflight."
    immutable(directory / "context-budget.json", context)
    if context["limit"] is not None and context["total_estimated"] > context["limit"]:
        immutable(directory / "unavailable.json", {"status":"missing", "reason":"input_context_budget", "failures":[]})
        raise ReportUnavailable("Report multimodal input exceeds its submission budget")
    failures = []
    for number in range(1, policy["max_attempts"] + 1):
        # Preserve the historical first-call path and every later independent answer.
        call = directory / ("call" if number == 1 else f"report-attempts/{number:02d}/call")
        failure_path = call.parent / ("report-failure.json" if number == 1 else "failure.json")
        if failure_path.exists():
            failure = load(failure_path)
            if failure.get("response_sha256") is not None and sha(call / "response.txt") != failure["response_sha256"]:
                raise IntegrityError("Original failed report answer changed")
            verify_inputs(call, model, packet, images)
            failures.append(failure)
            if failure.get("terminal"):
                break
            continue
        # Integrity errors from immutable inputs/receipts deliberately propagate.
        # Only provider transport failure and validated model-output failure recover.
        transport_error = None
        sent_packet=retry_packet(packet,failures,policy)
        allowance=output_tokens(failures,policy)
        try:
            raw = call_text(call, model, sent_packet["system_prompt"], sent_packet["user_text"], images,
                            attempts=1, retry_delay=0, max_new_tokens=allowance,meter_only=usage=="independent_final")
        except ProviderDispatchPaused:
            raise
        except ModelTransportError as exc:
            transport_error = exc
        if transport_error is None:
            returned = load(call / "returned.json")
            if returned["sha256"] != sha(call / "response.txt"):
                raise IntegrityError("Report transport receipt integrity mismatch")
        category = "transport" if transport_error else "json_format"
        error = transport_error
        if error is None:
            try:
                if returned.get("finish_reason") in {"length", "max_tokens", "max_output_tokens"}:
                    category = "capacity"
                    raise ValueError("Provider output capacity exhausted")
                report = decode_object(raw)
                category = "schema_or_evidence"
                validate(report, packet)
            except (ValueError, TypeError, KeyError) as exc:
                error = exc
        if error is not None:
            record = {"attempt": number, "category": category, "error_type": type(error).__name__,
                      "error": str(error), "provider_error":getattr(error,"provider_error",None), "call_path": str(call),
                      "retryable": error.retryable if isinstance(error, ModelTransportError) else True,
                      "terminal": isinstance(error, ModelTransportError) and not error.retryable,
                      "input_sha256": sha(call / "input.json"),
                       "response_sha256": sha(call / "response.txt") if (call / "response.txt").exists() else None,
                      "previous_failure": failures[-1]["call_path"] if failures else None}
            immutable(failure_path, record)
            failures.append(record)
            if isinstance(error, ModelTransportError) and not error.retryable:
                break
            continue
        selection = {"attempt": number, "call_path": str(call),
                     "input_sha256": sha(call / "input.json"),
                     "response_sha256": sha(call / "response.txt"),
                     "returned_sha256": sha(call / "returned.json"), "output_tokens_reserved":allowance,"policy": policy["version"]}
        immutable(directory / "selected-answer.json", selection)
        return report, selection
    immutable(directory / "unavailable.json", {"status": "missing", "reason": "report_recovery_exhausted", "failures": failures})
    raise ReportUnavailable("Report recovery exhausted; retain missing assessment and all attempts")


def verify_inputs(call, model, packet, images):
    sent = load(Path(call) / "input.json")
    packet=attempt_packet(call,packet)
    expected = {"system_prompt":packet["system_prompt"], "user_text":packet["user_text"],
                "images":[{"path":str(p), "sha256":sha(p)} for p in images],
                "model":model.model, "reasoning_effort":getattr(model,"reasoning_effort",None)}
    # An offline verifier has no live client; transport metadata must still
    # match the original input receipt alongside the model, prompt and evidence.
    call = Path(call)
    root = call.parents[2] if call.parent.parent.name == "report-attempts" else call.parent
    receipts = [root / "selected-answer.json", call.parent / "report-failure.json", call.parent / "failure.json"]
    bound = False
    for path in receipts:
        if not path.exists():
            continue
        receipt = load(path)
        if receipt.get("call_path") != str(call) or "input_sha256" not in receipt:
            continue
        if receipt["input_sha256"] != sha(call / "input.json"):
            raise IntegrityError("Original report input receipt changed")
        bound = True
    runtime_identity = getattr(model, "runtime_identity", None)
    if callable(runtime_identity):
        expected["transport"] = runtime_identity()
    elif "transport" in sent:
        if not bound or not isinstance(sent["transport"], dict):
            raise IntegrityError("Offline report transport identity has no original input receipt")
        expected["transport"] = sent["transport"]
    if sent != expected:
        raise IntegrityError("Original report call input identity changed")


def verify_answer(directory, report, *, project=lambda x: x):
    directory = Path(directory)
    selected = directory / "selected-answer.json"
    binding = load(selected) if selected.exists() else {"call_path": str(directory / "call")}
    call = Path(binding["call_path"])
    raw = call / "response.txt"
    if "input_sha256" in binding and sha(call / "input.json") != binding["input_sha256"]:
        raise IntegrityError("Selected original model input changed")
    if selected.exists() and (sha(raw) != binding["response_sha256"] or sha(call / "returned.json") != binding["returned_sha256"]):
        raise ValueError("Selected original model answer changed")
    if project(decode_object(raw.read_text(encoding="utf-8"))) != report:
        raise ValueError("Cached report differs from the original model answer")
    return call
