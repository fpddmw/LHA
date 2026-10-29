"""Pair unchanged model-led Planner handoffs with existing renderer baselines."""
import copy
import hashlib
import json
from pathlib import Path

from run_prompt_probe import digest, save

ROOT = Path(__file__).resolve().parents[2]
TASKS = [
    ('041', '041__short', 'out/planner_harness/20261029/041_storybook'),
    ('fewshot_004', 'fewshot_004__long', 'out/planner_harness/20261029/004_space_arena'),
    ('027', '027__short', 'out/planner_harness/20261029_comparison/027_etching'),
    ('024', '024__long', 'out/planner_harness/20261029_comparison/024_glitch'),
]


def main():
    summary=[]
    for renderer in ['bernini','ditto']:
        baseline=json.loads((ROOT/f'out/prompt_probe/20261029_{renderer}/cases.json').read_text(encoding='utf-8'))
        spec={k:copy.deepcopy(v) for k,v in baseline.items() if k!='cases'}
        spec.update(purpose='Paired generation using unchanged model-led Planner prompts on previously tested tasks',
                    expected_cases=4, evaluation_status='Metrics under development; generated-video quality is not inferred from Planner self-review',cases=[])
        for sid,base_id,plan_rel in TASKS:
            base=next(c for c in baseline['cases'] if c['case_id']==base_id)
            directory=ROOT/plan_rel
            if not (directory/'handoff.json').exists():continue
            handoff=json.loads((directory/'handoff.json').read_text(encoding='utf-8'))
            state=json.loads((directory/'state.json').read_text(encoding='utf-8'))
            prompt=(directory/'prompt.txt').read_text(encoding='utf-8')
            assert state['status']=='complete' and handoff['validation']['accepted']
            assert state['request']['text']==base['prompt'],(sid,'different user request')
            assert handoff['source']['sha256']==base['source_video_sha256']==digest(ROOT/base['source_video'])
            assert prompt==handoff['prompt']==state['proposal']['prompt']
            assert digest(directory/'prompt.txt')==handoff['prompt_sha256']
            case=copy.deepcopy(base)
            case.update(case_id=sid+'__planner',condition='planner',prompt=prompt,
                        user_requirement=base['prompt'],task_prompt_kind=base['condition'],
                        planner_run=plan_rel,planner_prompt_sha256=handoff['prompt_sha256'],
                        planner_handoff_sha256=digest(directory/'handoff.json'),
                        planner_model=state['config']['model'],planner_reasoning_effort=state['config']['reasoning_effort'],
                        planner_target_model=handoff['target_model'],
                        baseline_case_ids=[c['case_id'] for c in baseline['cases'] if c['sample_id']==sid],
                        comparison_note='Same immutable source, seed and renderer settings. Source prompt is handed off unchanged; no automatic shortening.')
            spec['cases'].append(case)
            if renderer=='bernini':
                summary.append({'sample_id':sid,'planner_run':plan_rel,'prompt_words':len(prompt.split()),
                    'source_sha256':base['source_video_sha256'],'prompt_sha256':handoff['prompt_sha256'],
                    'user_requirement':base['prompt'],'matched_baselines':case['baseline_case_ids']})
        run=ROOT/f'out/planner_probe/20261029_{renderer}';run.mkdir(parents=True,exist_ok=True)
        save(run/'cases.json',spec)
    root=ROOT/'out/planner_probe/20261029';root.mkdir(parents=True,exist_ok=True)
    save(root/'matched-plans.json',{'matched':summary,'planned_total':4,
         'excluded_existing_runs':[{'run':'001_cyber_xianxia','reason':'Different source/task; no matching case in the current ten-condition probe'},
                                   {'run':'001_narrow_robe','reason':'Different source/task; no matching case in the current ten-condition probe'}]})
    print(json.dumps({'prepared':len(summary),'samples':[s['sample_id'] for s in summary]}),flush=True)


if __name__=='__main__':main()
