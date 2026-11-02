"""Validate the single benchmark manifest and evidence-card isolation."""
from pathlib import Path
import collections
import hashlib
import json
import re
ROOT = Path(__file__).resolve().parents[1]

def validate(root=ROOT):
    root=Path(root)
    rows=json.loads((root/'benchmark_data/benchmark.json').read_text())
    audit=json.loads((root/'reports/benchmark-release-20261102/historical-evidence-audit.json').read_text())
    release=json.loads((root/'benchmark_data/release.json').read_text())
    ids=[r['sample_id'] for r in rows]
    assert len(ids)==len(set(ids))==release['count']
    assert ids==release['selected_ids']==sorted(ids)
    assert not set(ids)&set(release['excluded_ids'])
    assert collections.Counter(r['split'] for r in rows)==release['splits']
    assert {r['benchmark_version'] for r in rows}=={release['benchmark_version']}
    assert hashlib.sha256((root/'benchmark_data/benchmark.json').read_bytes()).hexdigest()==release['manifest_sha256']
    assert release['condition_count_per_method']==2*len(rows)
    assert all('is_fewshot' not in r and r['origin']!='fewshot' for r in rows)
    for r in rows:
        for field in ('source_video','prompt_file','prompt_short_file'):
            p=root/r[field]
            assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==r[field+'_sha256'],str(p)
        assert (root/r['prompt_file']).read_text().strip()==r['instruction']
        assert (root/r['prompt_short_file']).read_text().strip()==r['prompt_short']
        assert {p.name for p in (root/r['source_video']).parent.iterdir()}=={'video.mp4','prompt_long.txt','prompt_short.txt'}
    assert len({r['source_video_sha256'] for r in rows})==len(rows)
    for split in ('train','validation','test'):
        actual={p.name for p in (root/'benchmark_data'/split).iterdir() if p.is_dir()}
        assert actual=={r['sample_id'] for r in rows if r['split']==split},split
    for group in {r['source_group'] for r in rows}:
        assert len({r['split'] for r in rows if r['source_group']==group})==1
    exposed={r['sample_id'] for r in rows if r['legacy_id'] in audit['matches'] or r['evidence_card_exposed']}
    paths={root/name for name in audit['scanned_files']}
    paths.update(p for p in (root/'knowledge').rglob('*') if p.is_file() and p.suffix in ('.json','.jsonl','.md') and ('evidence' in p.parts or 'evidence_card' in p.name or 'evidence-card' in p.name))
    for path in paths:
        if not path.is_file():continue
        text=path.read_text(errors='replace').replace('\\','/')
        for r in rows:
            sid=r['sample_id'] if 'lha-benchmark-20261102-' in text else r['legacy_id']
            pattern=r'(?<![\w])'+re.escape(sid)+r'(?!\d)' if sid.startswith('fewshot_') else 'benchmark__'+sid+'__'
            if any(token in text for token in [r['source_video_sha256'],r['source_video'],r['legacy_source_video']]) or re.search(pattern,text):exposed.add(r['sample_id'])
    groups={r['source_group'] for r in rows if r['sample_id'] in exposed}
    violations=[r['sample_id'] for r in rows if (r['source_group'] in groups or r['evidence_group_forced_train']) and r['split']!='train']
    assert not violations, 'Evidence-card holdout leakage: '+str(violations)
    return {'count':len(rows),'version':release['benchmark_version'],'splits':dict(collections.Counter(r['split'] for r in rows)),'continuous_ids':ids==[f'{i:03d}' for i in range(1,len(rows)+1)],'direct_evidence_matches':len(exposed),'forced_training_including_source_groups':sum(r['source_group'] in groups for r in rows),'evidence_holdout_violations':violations}
if __name__=='__main__':print(json.dumps(validate(),indent=2))
