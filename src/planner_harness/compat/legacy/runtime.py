"""Explicit archived-workflow hooks, never implicit behavior of the creative loop."""
import json
from planner_harness.common import save
from planner_harness.knowledge import Knowledge


def raw_context(harness):
    from planner_harness.context import base_context
    return base_context(harness)


def context(harness):
    text, images, mapping = raw_context(harness)
    if harness.state['config'].get('context_version',1) < 2:
        return text, images, mapping
    from planner_harness.context import attachments,present
    payload = present(json.loads(text),harness.state,harness.knowledge)
    images,mapping = attachments(harness.state)
    payload['attached_images_in_order'] = mapping
    if harness.state['config'].get('rsi'):
        from planner_harness.compat.rsi.rsi_support import context as rsi_context
        payload = rsi_context(harness,payload)
    return json.dumps(payload,ensure_ascii=False,indent=2),images,mapping


def configure(harness, execution, rsi, mode):
    from planner_harness.execution import prepare_profile
    harness.knowledge = Knowledge(harness.root)
    harness.state['config']['execution'] = prepare_profile(execution,harness.root,harness.state['request'])
    if rsi is not None and rsi is not False:
        if mode != 'loop':
            raise ValueError('RSI is enabled only for continuous loop tasks')
        from planner_harness.compat.rsi.rsi_support import configure as configure_rsi
        configure_rsi(harness,rsi)


def system_prompt(harness, feedback_files):
    from planner_harness.compat import HARNESS_ROOT
    operations = (HARNESS_ROOT/'OPERATIONS.md').read_text(encoding='utf-8')
    manual = (harness.root/'knowledge/READING.md').read_text(encoding='utf-8')
    result = operations+'\n\n# Current knowledge reading manual\n\n'+manual
    if harness.state['config']['execution'].get('critic') or feedback_files:
        from critic_harness.adapter import PLANNER_MANUAL
        result += '\n\n'+PLANNER_MANUAL
    if harness.state['config'].get('rsi'):
        result += '\n\n'+(HARNESS_ROOT/'RSI.md').read_text(encoding='utf-8')
    return result


def verify_state(harness):
    from .task_criteria import verify_state as verify
    verify(harness.state)


def before_run(harness):
    if harness.state['config'].get('rsi'):
        from planner_harness.compat.rsi.rsi_support import auto_review
        return auto_review(harness)
    return False


def record_decision(harness,call_dir):
    if harness.state['config'].get('rsi'):
        save(call_dir/'decision-state.json',harness.state)


def call_model(harness,call_dir,user_text,images):
    if harness.state['config'].get('rsi'):
        from planner_harness.compat.rsi.rsi_calls import call_once
        return call_once(call_dir,harness.model,harness.system,user_text,images)
    return harness.model.predict_text(system_prompt=harness.system,user_text=user_text,image_paths=images,max_new_tokens=7000)
