"""Count, run and resume the full-population runs; reviewer self-review is optional."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def load_hosts(path, requested):
    """Accept one host or a named pair; linked files are relative to this config."""
    from planner_harness.common import load
    value = load(path)
    if 'hosts' in value:
        names = ['bernini', 'ditto'] if requested == 'both' else [requested] if requested else list(value['hosts'])
        hosts = {}
        for name in names:
            item = value['hosts'][name]
            hosts[name] = load(path.parent / item) if isinstance(item, str) else item
    else:
        name = value.get('renderer', {}).get('backend')
        if requested == 'both' or (requested and requested != name):
            raise ValueError('Selected backend requires a matching host config or a hosts mapping')
        hosts = {name: value}
    if set(hosts) - {'bernini', 'ditto'} or any(h.get('renderer', {}).get('backend') != n for n,h in hosts.items()):
        raise ValueError('Each host must declare its matching bernini/ditto renderer')
    return hosts


def main():
    from experiments import campaign
    from planner_harness.common import load
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['plan', 'run', 'status'])
    parser.add_argument('--config', type=Path, default=ROOT / 'configs/experiment-campaign.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'out/main-all67-v2')
    parser.add_argument('--host-config', type=Path)
    parser.add_argument('--backend', choices=['bernini', 'ditto', 'both'],
                        help='both runs separate Bernini/Ditto subdirectories; single-host configs infer the backend')
    parser.add_argument('--stage', choices=['main', 'self-review', *campaign.STAGES, 'score'], default='main')
    parser.add_argument('--execute', action='store_true', help='Actually submit generation/model/evaluation work')
    args = parser.parse_args()
    both = args.backend == 'both'
    if args.command == 'status':
        models = [n for n in ('bernini', 'ditto') if (args.output / n / 'campaign.json').exists()]
        if both:
            models = ['bernini', 'ditto']
        result = {n: campaign.status(args.output / n) for n in models} if both or (args.backend is None and models) else campaign.status(args.output)
    else:
        config = campaign.configuration(args.config)
        if args.command == 'plan':
            result = campaign.plan(ROOT, config)
            if both:
                result = {'models': {n: result for n in ('bernini', 'ditto')},
                          'main_max_generations': 2 * result['main_max_generations'],
                          'main_trajectories': 2 * result['main_trajectories']}
            else:
                result['backend'] = args.backend or 'bernini'
        else:
            if not args.execute:
                parser.error('run requires --execute; plan prints the matrix without running it')
            if both and not args.host_config and args.stage == 'score':
                hosts = {n: {'renderer': {'backend': n}} for n in ('bernini', 'ditto')}
            else:
                hosts = load_hosts(args.host_config, args.backend) if args.host_config else None
            if both or (hosts and len(hosts) > 1):
                if not hosts:
                    parser.error('both requires a host config mapping for Bernini and Ditto')
                result = campaign.execute_models(ROOT, args.output, config, hosts, args.stage, execute_paid=True)
            else:
                result = campaign.execute(ROOT, args.output, config, next(iter(hosts.values())) if hosts else None,
                                          args.stage, execute_paid=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
