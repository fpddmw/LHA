"""Compare saved-state prompt projections without calls, video decoding or mutation."""
import argparse
import copy
import importlib
import json
from pathlib import Path
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from planner_harness.common import load, save, sha
from planner_harness.creative_knowledge import CreativeKnowledge


def project(run, revision=None):
    originals = {}
    package = importlib.import_module('planner_harness')
    try:
        for name in ('working_memory', 'context'):
            full = 'planner_harness.' + name
            originals[name] = importlib.import_module(full)
            if revision:
                source = subprocess.check_output(['git', 'show', f'{revision}:src/planner_harness/{name}.py'], cwd=ROOT, text=True)
                module = types.ModuleType(full)
                module.__package__ = 'planner_harness'
                exec(compile(source, f'{revision}:{name}', 'exec'), module.__dict__)
                sys.modules[full] = module
                setattr(package, name, module)
        context = sys.modules['planner_harness.context']
        memory = sys.modules['planner_harness.working_memory']
        state = load(run / 'state.json')
        before = copy.deepcopy(state)
        system = (run / 'system-prompt.txt').read_text()
        harness = types.SimpleNamespace(state=state, system=system, knowledge=CreativeKnowledge(ROOT, run/'knowledge-snapshot.json'))
        raw, _, _ = context.base_context(harness)
        payload = context.present(json.loads(raw), state, harness.knowledge)
        images, mapping = context.attachments(state)
        payload['attached_images_in_order'] = mapping
        memory.visible(payload, state)
        payload, images, mapping = context.fit_multimodal(payload, state, system, images, mapping)
        user = json.dumps(payload, ensure_ascii=False, **({'indent': 2} if revision else {'separators': (',', ':')}))
        assert state == before, 'Projection mutated saved state'
        return payload, images, {'system_chars': len(system), 'user_chars': len(user), 'images': len(images),
            'components': {k: len(json.dumps(v, ensure_ascii=False, separators=(',', ':'))) for k, v in payload.items()}}
    finally:
        for name, module in originals.items():
            sys.modules['planner_harness.' + name] = module
            setattr(package, name, module)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', type=Path, nargs='+')
    parser.add_argument('--baseline', default='7c8add9')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    reports = []
    for run in args.runs:
        before_hash = sha(run/'state.json')
        old, old_images, previous = project(run, args.baseline)
        new, new_images, current = project(run)
        checks = {'request_unchanged': old['task'] == new['task'], 'images_unchanged': old_images == new_images,
                  'notes_unchanged': old['notes'] == new['notes'], 'evaluations_unchanged': old['evaluations'] == new['evaluations'],
                  'archive_unchanged': sha(run/'state.json') == before_hash}
        assert all(checks.values()), checks
        reports.append({'run': str(run), 'baseline': args.baseline, 'before': previous, 'after': current, 'checks': checks,
                        'user_chars_reduction': round(1-current['user_chars']/previous['user_chars'], 4)})
    result = {'scope': 'Offline projection of the same saved states; characters are not actual API token usage.', 'runs': reports}
    save(args.output, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
