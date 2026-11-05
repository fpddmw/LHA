"""Maintenance operations and a resumable upgrade from ambiguous old replies."""
import copy
import json
from pathlib import Path

from .common import load, save
from .json_output import action_envelope

PROTOCOL = 'maintenance-actions-v2'
INSTRUCTION = '''Submit one JSON object with "action" and "arguments", for example:
{"action":"skill","arguments":{"id":"lha-experience-analysis"}}
{"action":"read","arguments":{"source":"knowledge","id":"EX-P-every-plane"}}
After each operation, use its returned result to choose the next operation.
Read returns at most 8000 characters. Use its next_page action to continue;
increasing max_chars past 8000 returns the same page. Unique pages remain in
retained_reading, and operation_history records completed operations.
Finish with {"action":"contribute","arguments":{"text":"<your findings>","changes":[]}};
include supported entry changes when useful. maintenance_progress marks the final
step for contribution submission within the existing allowance.'''

PARAMETERS = {
    'skill': {'id'}, 'browse': {'id'}, 'search': {'query'},
    'read': {'source', 'id', 'start_line', 'start_char', 'max_chars'},
    'observe': {'video_id', 'start', 'end', 'count', 'crop'},
    'view_image': {'ids'}, 'note': {'text'}, 'contribute': {'text', 'changes'},
}
REQUIRED_TEXT = {
    'skill': ('id',), 'browse': (), 'search': ('query',), 'read': ('source', 'id'),
    'observe': ('video_id',), 'view_image': (), 'note': ('text',), 'contribute': ('text',),
}


def normalize(value, *, skills=None, final_step=False):
    """Accept unambiguous captured spellings; reject missing/unknown actions."""
    value = copy.deepcopy(value)
    if isinstance(value, dict) and not {'action', 'tool'}.intersection(value):
        names = set(value) - {'purpose'}
        if len(names) == 1 and next(iter(names)) in PARAMETERS:
            name = next(iter(names))
            args = value.pop(name)
            if isinstance(args, str) and name in {'skill', 'browse', 'search', 'note'}:
                key = {'skill': 'id', 'browse': 'id', 'search': 'query', 'note': 'text'}[name]
                args = {key: args}
            value.update(action=name, arguments=args)
    value = action_envelope(value, metadata={'purpose'})
    name, args = value.get('action'), value['arguments']
    if name not in PARAMETERS:
        raise ValueError('Choose a maintenance action: ' + ', '.join(PARAMETERS))
    if final_step and name != 'contribute':
        raise ValueError('This is the final maintenance step: submit action contribute with your findings; '
                         'use changes: [] for a prose-only conclusion. The preceding operation was not executed.')
    if name == 'observe' and 'video' in args:
        from .tool_interface import _alias
        _alias(args, 'video', 'video_id')
    unknown = set(args) - PARAMETERS[name]
    if unknown:
        raise ValueError(f'{name}: unsupported arguments {", ".join(sorted(unknown))}')
    for key in REQUIRED_TEXT[name]:
        if not isinstance(args.get(key), str) or not args[key].strip():
            raise ValueError(f'{name} requires nonempty {key}')
    if name == 'skill' and skills is not None and args['id'] not in skills:
        raise ValueError('Choose one of the available maintenance Skill IDs')
    if name == 'read' and args['source'] not in {'run', 'knowledge', 'reference'}:
        raise ValueError('read source is run, knowledge or reference')
    if name == 'view_image' and (not isinstance(args.get('ids'), list)
            or not 1 <= len(args['ids']) <= 8 or any(not isinstance(x, str) for x in args['ids'])):
        raise ValueError('view_image requires 1 to 8 image IDs')
    if name == 'contribute' and not isinstance(args.get('changes', []), list):
        raise ValueError('contribute changes must be a list')
    return value


def instructions(text):
    return text if INSTRUCTION in text else text + '\n\n' + INSTRUCTION


def calls_directory(folder):
    """Preserve old erroneous contexts; resume this maintenance attempt only."""
    folder = Path(folder)
    marker = folder / 'action-contract.json'
    if marker.exists():
        return folder / load(marker)['calls_directory']
    legacy = False
    for path in (folder / 'calls').glob('*/input.json'):
        payload = json.loads(load(path)['user_text'])
        if (payload.get('current_result', {}).get('error') == 'Choose an available maintenance action'
                and payload.get('loaded_skills') == {}):
            legacy = True
            break
    name = 'calls-v2' if legacy else 'calls'
    save(marker, {'protocol': PROTOCOL, 'calls_directory': name,
                  'previous_calls_retained': 'calls' if legacy else None})
    return folder / name
