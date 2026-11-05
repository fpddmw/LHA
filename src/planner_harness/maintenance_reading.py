"""Retain maintenance evidence by returned page, with usable continuation actions."""
import copy
import json
from pathlib import Path

from .execution import signature


def input_view(text):
    """Show a saved call's actual user context before its repeated system manual."""
    value = json.loads(text)
    if not isinstance(value, dict) or 'user_text' not in value:
        return text
    user = value['user_text']
    if isinstance(user, str):
        try:
            user = json.loads(user)
        except ValueError:
            pass
    return json.dumps({'user_text': user, **{k: v for k, v in value.items() if k != 'user_text'}},
                      ensure_ascii=False, indent=2)


def retain(cache, history, action, result, step):
    """Effective spans identify pages; request-size spelling does not."""
    kind, args = action['action'], action['arguments']
    item = {'step': step, 'action': copy.deepcopy(action)}
    if 'error' in result:
        item['error'] = result['error']
    elif kind in {'read', 'search', 'browse'}:
        if kind == 'read':
            result['source'] = args['source']
            result.setdefault('id', args['id'])
            result['effective_page_chars'] = len(result.get('text', ''))
            next_line = result.get('next_line')
            result['next_page'] = ({'action': 'read', 'arguments': {
                'source': args['source'], 'id': args['id'], 'start_line': next_line,
                'start_char': result.get('next_char', 0), 'max_chars': 8000}}
                if next_line is not None else None)
            identity = {k: result.get(k) for k in
                        ('source', 'id', 'start_line', 'start_char', 'end_line', 'end_char', 'text')}
            item['page'] = {k: result[k] for k in
                            ('source', 'id', 'start_line', 'start_char', 'end_line', 'end_char', 'next_page')
                            if k in result}
        else:
            identity = {'action': action, 'result': result}
        key = signature(identity)
        previous = next((row for row in cache if row['page_id'] == key), None)
        first = previous['first_step'] if previous else step
        if previous:
            result['already_read_at_step'] = first
            item['repeated_page_from_step'] = first
        cache[:] = [row for row in cache if row['page_id'] != key]
        cache.append({'page_id': key, 'first_step': first, 'action': copy.deepcopy(action),
                      'result': copy.deepcopy(result)})
    history.append(item)


def submission_call(call, final_step):
    """Correct an old last-step read in place; reuse all earlier saved decisions."""
    call = Path(call)
    if not final_step:
        return call
    from .model_answers import effective_response
    from .maintenance_actions import normalize
    from .json_output import decode_object
    response = effective_response(call)
    if response.is_file():
        try:
            if normalize(decode_object(response.read_text(), allow_prose=True))['action'] != 'contribute':
                return call / 'submission'
        except (ValueError, KeyError, TypeError):
            return call / 'submission'
    return call


def progress(step, total):
    final = step == total
    return {'step': step, 'total_steps': total, 'steps_remaining_including_this': total-step+1,
            'stage': 'submit' if final else 'inspect_and_write',
            'instruction': ('Submit contribute now with the findings supported by the retained evidence. '
                            'A prose-only conclusion uses changes: [].'
                            if final else 'Read the material needed for a useful contribution, then submit contribute. '
                            'Use retained_reading and operation_history for material already read; '
                            'use next_page to continue a document. The final step is for submission.')}
