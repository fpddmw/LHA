"""Independently verify the English edition against original sources and baseline."""
import ast
import dataclasses
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote
import zipfile

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
K = ROOT / 'knowledge'
manifest = json.loads((K / 'source-map.json').read_text())
with zipfile.ZipFile(WORK / 'before-english.zip') as archive:
    baseline = json.loads(archive.read('knowledge/source-map.json'))
records = {int(r['no']): r for r in json.loads((ROOT / 'zyx/styles.json').read_text())}
errors = []
CJK = re.compile('[\u3400-\u9fff\uf900-\ufaff\U00020000-\U0002fa1f]')


def check(condition, message):
    if not condition:
        errors.append(message)


def object_digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def blocks(text, kind):
    return re.findall(r'```' + kind + r'\n(.*?)\n```', text, re.S)


def shape(value):
    if isinstance(value, dict):
        return {key: shape(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [shape(item) for item in value]
    return type(value).__name__


def source_refs(data):
    refs = []
    for row in data['entries'] + data['domain_references']:
        refs.extend(row[key] for key in ('source', 'template', 'image') if key in row)
    return refs + data['supporting_sources']


templates = {}
all_ids = []
for path in (ROOT / 'src/skills/templates').rglob('*.py'):
    if path.name.startswith('__'):
        continue
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SKILLS' for t in node.targets):
            rows = ast.literal_eval(node.value)
            templates[path.relative_to(ROOT).as_posix()] = rows
            all_ids.extend(row['strategy_id'] for row in rows)

mapped_ids, mapped_records = [], []
shots = frames = translated_bases = preserved_bases = 0
for entry in manifest['entries']:
    text = (ROOT / entry['path']).read_text()
    jsons = [json.loads(block) for block in blocks(text, 'json')]
    src = entry.get('template', entry['source'])
    original_template = templates[src['path']][src['selector']['SKILLS_index']]
    mapped_ids.append(src['selector']['strategy_id'])
    check(src['selector']['strategy_id'] == original_template['strategy_id'], f"Wrong selector: {entry['id']}")
    if entry['type'] == 'opuscar_complete':
        no = entry['source']['selector']['no']
        mapped_records.append(no)
        original = records[no]
        check(entry['record_sha256'] == object_digest(original), f'Original record hash: {no}')
        check(jsons[-1] == original_template, f'Changed legacy template: {no}')
        metadata = jsons[0]
        expected_metadata = {key: original[key] for key in ('no', 'year', 'title_en', 'decade', 'kind', 'tone', 't0_seconds', 'duration_seconds', 'style_en', 'frame')}
        check(metadata == expected_metadata, f'Metadata changed: {no}')
        check(entry['original_fields'] == list(original), f'Original field inventory: {no}')
        for key in ['blend_en', 'desc_en', 'prompt_en', 'direction_en', 'references']:
            values = original[key] if isinstance(original[key], list) else [original[key]]
            for value in values:
                check(value in text, f'Missing English source text: {no} {key}')
        cursor = -1
        for index, shot in enumerate(original['shots'], 1):
            heading = f"#### {index}. {shot['name']} | {shot['seconds']} seconds"
            pos = text.find(heading)
            check(pos > cursor and pos >= 0, f'Shot order or metadata: {no} {index}')
            cursor = pos
            check(shot['text_en'] in text, f'Shot text changed: {no} {index}')
        check(entry['shots'] == len(original['shots']), f'Shot count: {no}')
        check(f"../../zyx/{original['frame']}" in text, f'Missing image link: {no}')
        image = ROOT / entry['image']['path']
        check(image.is_file() and image.read_bytes()[:2] == b'\xff\xd8', f'Invalid image: {no}')
        shots += len(original['shots'])
        frames += 1
    else:
        decoded = jsons[0]
        check(entry['record_sha256'] == object_digest(original_template), f"Base original hash: {entry['id']}")
        check(entry['reading_edition_sha256'] == object_digest(decoded), f"Base translation hash: {entry['id']}")
        check(shape(decoded) == shape(original_template), f"Base key/type/length changes: {entry['id']}")
        expected_translated = [key for key, value in original_template.items() if CJK.search(json.dumps(value, ensure_ascii=False))]
        check(set(entry['translated_fields']) == set(expected_translated), f"Translation field scope: {entry['id']}")
        for key, value in original_template.items():
            if key not in expected_translated:
                check(decoded[key] == value, f"Already-English field changed: {entry['id']} {key}")
            else:
                check(decoded[key] != value and not CJK.search(json.dumps(decoded[key], ensure_ascii=False)), f"Untranslated value: {entry['id']} {key}")
        if expected_translated:
            check('attributed translation' in text, f"Missing translation label: {entry['id']}")
            translated_bases += 1
        else:
            preserved_bases += 1
    check('## Editorial reading and design relationships' in text and '## Further reading' in text, f"Missing editorial sections: {entry['id']}")

check(sorted(mapped_ids) == sorted(all_ids), 'Template coverage is not one to one')
check(len(set(mapped_ids)) == 111, 'Template ID count')
check(sorted(mapped_records) == sorted(records), 'OPUSCAR coverage is not one to one')
check(shots == 302 and frames == 98, 'Shot/image count')
check(translated_bases == 7 and preserved_bases == 6, 'Base reading-edition coverage')

card_path = ROOT / 'scripts/eval/bench_v3/skills_v3.py'
spec = importlib.util.spec_from_file_location('english_validation_cards', card_path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
variants = 0
check({row['source']['selector']['CARDS_key'] for row in manifest['domain_references']} == set(module.CARDS), 'Domain coverage')
for entry in manifest['domain_references']:
    key = entry['source']['selector']['CARDS_key']
    text = (ROOT / entry['path']).read_text()
    original = dataclasses.asdict(module.CARDS[key])
    check(json.loads(blocks(text, 'json')[0]) == json.loads(json.dumps(original)), f'Card values: {key}')
    check(entry['record_sha256'] == object_digest(original), f'Card record hash: {key}')
    module.route = lambda _, selected=key: selected
    expected = [module.card_block('', **opts) for opts in ({}, {'decisive': True}, {'execution_only': True})]
    check(blocks(text, 'text') == expected, f'Card variant wording: {key}')
    variants += len(expected)

# Compare source references and navigation to the baseline, not just the rebuilt map.
for group in ['entries', 'domain_references']:
    old_rows = {row['id']: row for row in baseline[group]}
    new_rows = {row['id']: row for row in manifest[group]}
    check(new_rows.keys() == old_rows.keys(), f'Stable IDs: {group}')
    for key, old in old_rows.items():
        new = new_rows[key]
        for field in ['path', 'source', 'template', 'image', 'record_sha256', 'preserved_variants']:
            check(new.get(field) == old.get(field), f'Baseline mismatch: {key} {field}')
        application_members = {'opuscar-024', 'opuscar-038', 'opuscar-053', 'opuscar-063', 'opuscar-097', 'base-clean_lab', 'domain-sci_fi_modern'}
        expected_guides = old['guides'] + (['design-expression'] if key in application_members else [])
        check(new['guides'] == expected_guides, f'Topic memberships changed beyond approved additions: {key}')
        check([x['id'] for x in new['related']] == [x['id'] for x in old['related']], f'Related targets changed: {key}')
        check(all(x['reason'].strip() and not CJK.search(x['reason']) for x in new['related']), f'Related reasons: {key}')
expected_guides = [(r['id'], r['path']) for r in baseline['guides']] + [('design-expression', 'knowledge/guides/design-expression.md')]
check([(r['id'], r['path']) for r in manifest['guides']] == expected_guides, 'Guide IDs/paths changed beyond approved addition')
check(manifest['totals'] == {**baseline['totals'], 'guides': 7, 'model_experience_records': 1}, 'Coverage totals changed beyond approved additions')
check([(s['path'], s['sha256']) for s in manifest['supporting_sources']] == [(s['path'], s['sha256']) for s in baseline['supporting_sources']], 'Supporting source baseline changed')
sources = source_refs(baseline)
for source in sources:
    path = ROOT / source['path']
    check(path.is_file(), f'Missing original source: {source["path"]}')
    if path.is_file():
        check(hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256'], f'Original source changed since baseline: {source["path"]}')

# Verify the new experience chain against the existing experiment, including actual media hashes.
probe = ROOT / 'out/prompt_probe/20261029_bernini'
cases = json.loads((probe / 'cases.json').read_text())
experiences = manifest.get('model_experience', [])
check(len(experiences) == 1, 'Model-experience count')
experience = experiences[0]
check(experience['id'] == 'bernini-r-20261029' and experience['model'] == cases['model'] and experience['model_revision'] == cases['model_revision'], 'Experience identity/model mismatch')
check([r['id'] for r in experience['conditions']] == [r['case_id'] for r in cases['cases']], 'Experience condition coverage/order')
experience_body = (ROOT / experience['path']).read_text()
check(blocks(experience_body, 'text') == [c['prompt'] for c in cases['cases']], 'Verbatim experimental prompt mismatch')
experience_sources = list(experience['sources'])
for case, row in zip(cases['cases'], experience['conditions']):
    case_input = json.loads((ROOT / row['input']['path']).read_text())
    result = json.loads((ROOT / row['result']['path']).read_text())
    check(all(case_input[k] == v for k, v in case.items()), f"Case/input mismatch: {case['case_id']}")
    check(result['case_id'] == case['case_id'] and result['status'] == 'complete', f"Incomplete result: {case['case_id']}")
    check(row['output_video']['sha256'] == result['output_sha256'], f"Output metadata mismatch: {case['case_id']}")
    check(row['source_video'] == {'path': case['source_video'], 'sha256': case['source_video_sha256']}, f"Source metadata mismatch: {case['case_id']}")
    experience_sources.extend(row[k] for k in ['source_video', 'input', 'result', 'judgment', 'output_video'])
for ref in experience_sources:
    path = ROOT / ref['path']
    check(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == ref['sha256'], f"Experience source/media hash: {ref['path']}")

working_paths = [p for p in K.rglob('*') if p.is_file()]
working_paths += [ROOT / 'docs/skill-reorganization-plan.md', ROOT / 'docs/skill-reorganization-discussion.md']
check(manifest['working_language'] == 'en', 'Manifest working language')
links_by_file = {}
link_count = 0
for path in working_paths:
    body = path.read_text()
    check(not CJK.search(body), f'Chinese content in working file: {path.relative_to(ROOT)}')
    if path.suffix != '.md':
        continue
    visible = re.sub(r'```.*?```', '', body, flags=re.S)
    destinations = []
    for match in re.finditer(r'!?\[[^\]\n]+\]\(([^)\n]+)\)', visible):
        href = match[1].strip('<>')
        if re.match(r'[a-zA-Z]+://', href) or href.startswith('mailto:'):
            continue
        rawpath, _, fragment = href.partition('#')
        target = (path.parent / unquote(rawpath)).resolve() if rawpath else path
        check(target.is_file(), f'Broken link: {path.relative_to(ROOT)} -> {href}')
        if fragment and target.is_file() and target.suffix == '.md':
            headings = re.findall(r'^#+\s+(.+)$', target.read_text(), re.M)
            slugs = [re.sub(r'[^\w\-\s]', '', h.lower()).replace(' ', '-') for h in headings]
            check(unquote(fragment) in slugs, f'Broken anchor: {path.relative_to(ROOT)} -> {href}')
        destinations.append(target)
        link_count += 1
    links_by_file[path.resolve()] = destinations
    # Editorial tables should retain the same number of cells within each table.
    widths = []
    for line in visible.splitlines() + ['']:
        if line.startswith('|'):
            widths.append(len(re.findall(r'(?<!\\)\|', line)))
        else:
            if widths:
                check(len(set(widths)) == 1, f'Malformed table: {path.relative_to(ROOT)}')
            widths = []

map_links = links_by_file[(K / 'README.md').resolve()]
for row in manifest['entries'] + manifest['domain_references'] + manifest['guides'] + experiences:
    check((ROOT / row['path']).resolve() in map_links, f"Map orphan: {row['id']}")
for guide in manifest['guides']:
    path = (ROOT / guide['path']).resolve()
    for row in manifest['entries'] + manifest['domain_references']:
        if guide['id'] in row['guides']:
            check((ROOT / row['path']).resolve() in links_by_file[path], f"Guide entry missing: {guide['id']} -> {row['id']}")

stats = {
    'edition': 'English working edition with design-application revision', 'working_files_checked': len(working_paths),
    'working_files_with_chinese': sum(bool(CJK.search(path.read_text())) for path in working_paths),
    'complete_entries': len(manifest['entries']), 'template_ids_verified': len(set(mapped_ids)),
    'opuscar_records_verified': len(mapped_records), 'english_original_shots_verified': shots,
    'reference_images_verified': frames, 'translated_base_templates': translated_bases,
    'unchanged_english_base_templates': preserved_bases, 'domain_cards_verified': len(manifest['domain_references']),
    'card_variants_verified': variants, 'guides': len(manifest['guides']),
    'topic_memberships_preserved': sum(len(row['guides']) for row in baseline['entries'] + baseline['domain_references']),
    'topic_memberships_current': sum(len(row['guides']) for row in manifest['entries'] + manifest['domain_references']),
    'related_edges_preserved': sum(len(row['related']) for row in manifest['entries'] + manifest['domain_references']),
    'local_links_checked': link_count, 'original_source_references_verified_against_baseline': len(sources),
    'model_experience_records': len(experiences), 'experiment_conditions_verified': len(experience['conditions']),
    'experience_source_and_media_references_verified': len(experience_sources),
    'errors': errors, 'status': 'passed' if not errors else 'failed',
}
(WORK / 'validation.json').write_text(json.dumps(stats, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(stats, ensure_ascii=False, indent=2))
sys.exit(1 if errors else 0)

