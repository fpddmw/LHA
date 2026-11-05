"""Recover model response formatting within the original decision step."""
import json
import os
from pathlib import Path

from .common import load, save, sha
from .model_call import ModelTransportError, call_text, restore_model
from .json_output import decode_object
from .lock import RunLock


class ModelAnswerUnavailable(ModelTransportError):
    failure_kind = "model_answer_unavailable"

    def __init__(self, message, *, call=None):
        super().__init__(message, retryable=True)
        self.failure_kind = "model_answer_unavailable"
        self.call = str(call) if call is not None else None


def call_object(directory, model, system, user, images, *, validate=None,
                allow_prose=True, initial=None, max_new_tokens=7000):
    """Reuse valid replies; repair invalid JSON in-place without executing actions.

    Original replies and every correction have their own durable transport receipt.
    The first usable response wins; this does not judge content or select actions.
    """
    directory = Path(directory)
    recovery = directory / 'format-recovery'
    limit = int(os.environ.get('LHA_MODEL_FORMAT_ATTEMPTS', '12'))
    if limit < 1:
        raise ValueError('LHA_MODEL_FORMAT_ATTEMPTS must be positive')
    with RunLock(recovery):
        selected = recovery / 'selected.json'
        if selected.exists():
            receipt = load(selected)
            path = Path(receipt['response_path'])
            if sha(path) != receipt['response_sha256']:
                from .integrity import IntegrityError
                raise IntegrityError('Selected original response changed')
            value = decode_object(path.read_text(encoding='utf-8'), allow_prose=allow_prose)
            if validate:
                validate(value)
            return value, receipt
        binding_path = directory / 'input.json'
        if binding_path.exists():
            binding = load(binding_path)
            model = restore_model(model, binding)
            system, user = binding['system_prompt'], binding['user_text']
            images = [r['path'] for r in binding['images']]
        failure = None
        window = recovery / 'window.json'
        old = load(window) if window.exists() else {}
        last = int(old.get('last', limit)) + (limit if old.get('exhausted') else 0)
        save(window, {'last': last, 'exhausted': False})
        for number in range(last):
            call = directory if number == 0 else recovery / f'{number:02d}' / 'call'
            if number == 0 and isinstance(initial, str) and initial.strip():
                raw = initial
            else:
                correction = user
                if failure:
                    correction = json.dumps({
                        'original_input': user,
                        'previous_response': failure['response'],
                        'format_error': failure['error'],
                        'response_instruction': 'Return the requested JSON response for this same step. '
                            'The preceding reply was not executed. Preserve your intended decision and '
                            'substantive judgments; use the available operation names and parameter forms.'
                    }, ensure_ascii=False)
                raw = call_text(call, model, system, correction, images, max_new_tokens=max_new_tokens)
            try:
                value = decode_object(raw, allow_prose=allow_prose)
                if validate:
                    validate(value)
            except (ValueError, KeyError, TypeError) as exc:
                failure = {'response': raw, 'error': str(exc), 'type': type(exc).__name__}
                save(recovery / f'{number:02d}' / 'invalid.json', failure)
                continue
            path = call / 'response.txt'
            # Legacy runner caches may predate transport receipts. Retain their
            # exact original text without manufacturing a provider receipt.
            if not path.exists():
                from .common import write_atomic
                path = recovery / 'legacy-response.txt'
                write_atomic(path, raw)
            receipt = {'attempt': number, 'call_path': str(call),
                       'response_path': str(path), 'response_sha256': sha(path)}
            save(selected, receipt)
            return value, receipt
        save(window, {'last': last, 'exhausted': True})
        raise ModelAnswerUnavailable('Response format recovery exhausted; original step remains resumable', call=directory)


def effective_response(directory):
    """The accepted answer for evidence readers; original text remains archived."""
    directory = Path(directory)
    for path in (directory / 'effective-answer.json', directory / 'format-recovery/selected.json'):
        if path.exists():
            return Path(load(path)['response_path'])
    return directory / 'response.txt'
