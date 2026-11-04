"""Reuse original task records; software/default differences are provenance."""
from pathlib import Path
from .common import load, save
from .execution import signature


def record(directory, name, saved, proposed):
    if saved == proposed:
        return
    def public(value):
        if isinstance(value, dict):
            return {k: ('[redacted]' if any(s in k.lower() for s in ('api_key', 'password', 'access_token', 'refresh_token')) else public(v)) for k,v in value.items()}
        if isinstance(value, list):return [public(v) for v in value]
        return value
    body = {'field': name, 'saved': public(saved), 'current': public(proposed),
            'action': 'Continue original work; retain completed steps and generation accounting'}
    path = Path(directory)/'upgrade-history'/(name.replace('/', '_')+'-'+signature(body)+'.json')
    if not path.exists():save(path, body)


def retain(path, proposed):
    """A saved phase/configuration is authoritative, even after a code update."""
    path = Path(path)
    if path.exists():
        saved = load(path)
        record(path.parent, path.stem, saved, proposed)
        return saved
    save(path, proposed)
    return proposed


def cache_directory(parent, proposed, keys):
    """Find an existing operation in this task's cache, independent of code hash."""
    parent = Path(parent)
    matches = []
    for path in sorted(parent.glob('*/identity.json')):
        saved = load(path)
        if all(saved.get(key) == proposed.get(key) for key in keys):
            matches.append((path.parent, saved))
    if matches:
        # Preserve the earliest established result if an old upgrade forked caches.
        directory, saved = min(matches, key=lambda row: (not (row[0]/'result.json').exists(), (row[0]/'identity.json').stat().st_mtime_ns))
        record(directory, 'implementation', saved, proposed)
        return directory, saved
    return parent/signature(proposed), proposed
