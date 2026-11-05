"""Shared readiness and dispatch decision for recorded permanent API failures."""
from pathlib import Path

from .common import load, sha


def blocked_permanent_failure(directory):
    """An existing explicit recovery can advance past a permanent rejection."""
    directory = Path(directory)
    if (directory / 'response.txt').exists() or any((directory / 'attempts').glob('*/response.txt')):
        return None
    failures = []
    for path in (directory / 'attempts').glob('*/failed.json'):
        if not path.parent.name.isdigit():
            continue
        failure = load(path)
        if failure.get('retryable') is False and failure.get('failure_kind') != 'integrity_error':
            failures.append((int(path.parent.name), failure))
    if not failures:
        return None
    policy_path = directory / 'allowance.json'
    policy = load(policy_path) if policy_path.exists() else None
    first = 1
    for path in (directory / 'recoveries').glob('*.json'):
        recovery = load(path)
        # Automatic runtime windows have no next/input/reason authorization.
        if (isinstance(policy, dict) and recovery.get('next') == policy
                and str(recovery.get('reason', '')).strip()
                and (directory / 'input.json').exists()
                and recovery.get('input_sha256') == sha(directory / 'input.json')):
            first = max(first, policy['first'])
    blocked = [(number, value) for number, value in failures if number >= first]
    if not blocked:
        return None
    number, failure = max(blocked, key=lambda row: row[0])
    return {'attempt': number, 'failure': failure}
