"""Archived legacy/RSI actions; the creative runner dispatches before this boundary."""
import copy
import json
import re
from pathlib import Path
from planner_harness.common import load,save,sha,page,stamp

def operate(self, response, event_id):
    action, args = (response.get('action', response.get('tool')), response.get('arguments', {}))
    if not isinstance(args, dict):
        raise ValueError('arguments must be an object')
    from planner_harness.creative import active
    if 'note' in response:
        self.remember(response['note'])
    if 'workspace' in response:
        self.update_workspace(response['workspace'])
    if action == 'browse':
        return self.knowledge.browse(args.get('id', 'map'))
    if action == 'search':
        return self.knowledge.search(args['query'], args.get('limit', 8))
    if action == 'read':
        targets = args.get('targets', [])
        if not isinstance(targets, list) or not 1 <= len(targets) <= 4:
            raise ValueError('read accepts 1 to 4 targets')
        results = []
        for target in targets:
            try:
                options = {}
                result = self.knowledge.read(target['id'], target.get('start_line', 1), target.get('section'), **options)
                read_id = f"read-{len(self.state['reads']) + 1:04d}"
                result['read_id'] = read_id
                self.state['reads'][read_id] = {k: result[k] for k in ('id', 'path', 'sha256', 'start_line', 'end_line', 'next_line')}
                self.state['reads'][read_id]['event_id'] = event_id
                self.state['reads'][read_id].update({k: result[k] for k in ('start_char', 'end_char', 'next_char') if k in result})
                results.append(result)
            except (ValueError, KeyError, OSError) as exc:
                results.append({'target': target, 'error': str(exc)})
        return {'materials': results}
    if action == 'observe':
        return self.observe(args, event_id)
    if action == 'view_reference':
        references = self.knowledge.references(args['id'])
        self.state['reference_images'] = references
        self.state['reference_image'] = references[-1]
        return references[0] if len(references) == 1 else {'images': references}
    if action == 'workspace':
        if args:
            self.update_workspace(args)
        return {'saved': True, 'workspace': self.state['workspace']}
    if action == 'note':
        self.remember(args.get('text', ''), append=args.get('append', True))
        return {'saved': True}
    if action == 'lesson':
        self.remember(args.get('text', ''), append=args.get('append', True))
        return {'saved': True, 'scope': 'Optional task-local working judgment'}
    if action == 'requirements':
        if not self.state['config'].get('rsi'):
            raise ValueError('Requirements operation needs an RSI run')
        from planner_harness.ledger import set_requirements
        return set_requirements(self.state, args.get('items'), args.get('reason', ''))
    if action == 'video':
        identity = args.get('id', 'source')
        if identity not in self.state.get('videos', {}):
            raise ValueError('Unknown video ID')
        return self.state['videos'][identity]
    if action == 'criteria_objection':
        from planner_harness.task_criteria import objection
        return objection(self.state, args.get('text'), args.get('evidence'))
    if action == 'delivery_candidate':
        identity = args.get('video', args.get('id', 'source'))
        if identity not in self.state.get('videos', {}):
            raise ValueError('Unknown video ID')
        self.state['delivery_candidate'] = identity
        return {'video': identity, 'scope': 'Current intended delivery; does not select render input or finish the task'}
    if action in {'generate', 'evaluate', 'critique'}:
        from planner_harness.execution import request_job
        return request_job(self, action, args, event_id)
    if action == 'finish':
        if self.state['config'].get('mode', 'plan') != 'loop':
            raise ValueError('Use submit with an English prompt to finish a planning-only run')
        identity = args.get('video')
        if identity is not None and identity not in self.state['videos']:
            raise ValueError('Choose an existing video ID, or omit it when no result is ready')
        if re.search('[\\u3400-\\u9fff]', json.dumps(args, ensure_ascii=False)):
            raise ValueError('Use English for working output')
        reason = args.get('stop_reason', 'satisfied' if identity not in {None, 'source'} else 'no_promising_attempt')
        if reason not in {'satisfied', 'no_promising_attempt', 'budget', 'execution_failure'}:
            raise ValueError('Unknown finish stop_reason')
        extra = {'stop_reason': reason}
        if self.state['config'].get('rsi'):
            from planner_harness.ledger import build
            if args.get('stop_reason') not in {'satisfied', 'no_promising_attempt', 'budget', 'execution_failure'}:
                raise ValueError('RSI finish needs stop_reason: satisfied/no_promising_attempt/budget/execution_failure')
            memory = build(self.state)
            rows = memory.get('candidates', {}).get(identity, {}).get('verdicts', {})
            unmet = [r['id'] for r in self.state.get('requirements', {}).get('items', []) if rows.get(r['id'], 'unknown') != 'pass']
            extra = {'stop_reason': args['stop_reason'], 'unmet': unmet, 'delivery_status': 'budget_limited' if args['stop_reason'] == 'budget' else 'execution_failed' if args['stop_reason'] == 'execution_failure' else 'selected_with_unresolved_requirements' if unmet else 'criteria_satisfied', 'added_requirement_suggestions': memory.get('candidates', {}).get(identity, {}).get('added_requirements', []), 'scope': 'Planner stop reason; measured unresolved items are retained separately.'}
        from planner_harness.delivery import finish_status
        status = finish_status(self.state, reason, identity)
        self.state.update(status=status, final={'video': identity, 'message': args.get('message', ''), 'outcome': 'selected_video' if identity else 'stopped_without_video', **extra})
        save(self.output / 'final.json', self.state['final'])
        return self.state['final']
    if action == 'history':
        options = {}
        if 'feedback' in args:
            if 'event_id' in args:
                raise ValueError('Choose feedback or event_id')
            feedback = self.state.get('evaluations', {}).get(args['feedback'])
            if feedback is None:
                raise ValueError('Unknown feedback ID')
            return page(json.dumps(feedback, ensure_ascii=False, indent=2), args.get('start_line', 1), **options)
        matches = [e for e in self.state['events'] if e['event_id'] == args.get('event_id')]
        if not matches:
            raise ValueError('Unknown event ID')
        value = matches[0].get('result', {}) if args.get('result_only') else matches[0]
        return page(json.dumps(value, ensure_ascii=False, indent=2), args.get('start_line', 1), **options)
    if action == 'submit':
        return self.submit(args)
    raise ValueError(f'Unknown operation: {action}')

def submit(self, proposal):
    proposal = {"understanding": "", "proposal": "", "self_review": "", "sources": [], "unresolved": [], **proposal}
    issues = []
    for field in ("prompt",):
        if not isinstance(proposal.get(field), str) or not proposal[field].strip():
            issues.append(f"Provide nonempty English {field}")
    if re.search(r"[\u3400-\u9fff]", json.dumps(proposal, ensure_ascii=False)):
        issues.append("Use English for the planning output")
    if not isinstance(proposal.get("sources"), list) or not isinstance(proposal.get("unresolved"), list):
        issues.append("sources and unresolved must be arrays")
    for citation in proposal.get("sources", []) if isinstance(proposal.get("sources"), list) else []:
        receipt = self.state["reads"].get(citation.get("read_id")) if isinstance(citation, dict) else None
        if not receipt or not isinstance(citation.get("use"), str) or not citation["use"].strip():
            issues.append("Citations need an actual returned read_id and a description of use")
        elif self.knowledge.read(receipt["id"])["sha256"] != receipt["sha256"]:
            issues.append(f"Cited source changed since reading: {receipt['path']}")
    version = len(self.state["submission_attempts"]) + 1
    result = {"version": version, "accepted": not issues, "issues": issues,
              "renderer_preflight": "pending: no renderer tokenizer/configuration is loaded in this Planner-only run",
              "renderer_submission": "not performed"}
    save(self.output / "proposals" / f"{version:03d}.json", {"proposal": proposal, "validation": result})
    self.state["submission_attempts"].append(result)
    if not issues:
        self.state["proposal"] = proposal
        self.state["status"] = "complete" if self.state["config"].get("mode", "plan") == "plan" else "running"
        save(self.output / "proposal.json", proposal)
        (self.output / "prompt.txt").write_text(proposal["prompt"], encoding="utf-8")
        save(self.output / "handoff.json", {"source": self.state["request"]["source"],
             "target_model": self.state["request"]["target_model"], "prompt": proposal["prompt"],
             "prompt_sha256": sha(self.output / "prompt.txt"), "validation": result})
    return result
