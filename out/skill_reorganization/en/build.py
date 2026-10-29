"""Build the English working edition from authored translations and unchanged sources."""
import ast
import dataclasses
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
OUT = ROOT / 'knowledge'
GUIDES = {
    'meaning': 'Video meaning and design possibilities',
    'theme': 'Subject matter and visual language',
    'media': 'How different media form an image',
    'time': 'Composition, light, and time',
    'combination': 'Combining styles and methods',
    'experience': 'The conditions behind generation experience',
    'design-expression': 'From knowledge to a visual proposal',
}
APPLICATION_REASONS = {
    '024': 'Compare displaced color and ink with the pencil-and-wash choice in the storybook walkthrough.',
    '038': 'Compare a sculpted storybook interpretation with the paper-based direction developed for benchmark 041.',
    '053': 'Follow paper white and transparent glazing into a new bright-interior illustration proposal.',
    '063': 'Follow visible pencil and transparent color into a new storybook proposal, with journal and sunset choices kept in their source context.',
    '097': 'Follow the relationship between an emitting part and receiving surfaces into a proposed luminous tabletop rim.',
    'base-clean_lab': 'See technical materials and illumination adapted to a requested sports arena.',
    'domain-sci_fi_modern': 'See technical vocabulary selected for athletic clothing, walls, and a specific light-emitting table part.',
}

def dump(x):
    return json.dumps(x, ensure_ascii=False, indent=2)

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def object_digest(x):
    return hashlib.sha256(json.dumps(x, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

def source(p, selector=None):
    result = {'path': p.relative_to(ROOT).as_posix(), 'sha256': digest(p)}
    if selector is not None:
        result['selector'] = selector
    return result

def slug(key):
    return f'opuscar-{int(key):03d}' if key.isdigit() else key

def target(key):
    return '../domain-references/' + key[7:] + '.md' if key.startswith('domain-') else '../entries/' + slug(key) + '.md'

editorials = {}
for p in sorted(WORK.glob('editorial-*.json')):
    original = json.loads((WORK.parent / p.name).read_text())
    translated = json.loads(p.read_text())
    assert original.keys() == translated.keys(), p.name
    for key, row in translated.items():
        old = original[key]
        assert len(old['related']) == len(row['reasons']), key
        row['related'] = [[ref[0], reason] for ref, reason in zip(old['related'], row.pop('reasons'))]
        row['guides'] = list(old['guides'])
        normalized = 'domain-' + key if p.name == 'editorial-domains.json' else key
        if normalized in APPLICATION_REASONS:
            row['guides'].append('design-expression')
        assert normalized not in editorials
        editorials[normalized] = row

records = json.loads((ROOT / 'zyx/styles.json').read_text())
templates = {}
for p in sorted((ROOT / 'src/skills/templates').rglob('*.py')):
    if p.name.startswith('__'):
        continue
    for node in ast.parse(p.read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SKILLS' for t in node.targets):
            for i, row in enumerate(ast.literal_eval(node.value)):
                m = re.match(r'opuscar_(\d+)_', row['strategy_id'])
                key = f'{int(m[1]):03d}' if m else 'base-' + row['strategy_id']
                assert key not in templates
                templates[key] = (p, i, row)

translations = json.loads((WORK / 'template-translations.json').read_text())
TITLES = {f"{r['no']:03d}": f"{r['no']:03d} | {r['title_en']}: {r['style_en']}" for r in records}
TITLES.update({k: row['title'] for k, row in editorials.items() if not k.isdigit()})

def front(key):
    row = editorials[key]
    s = f'# {TITLES[key]}\n\n[Knowledge map](../README.md) · [Reading manual](../READING.md)\n\n'
    s += row['summary'] + '\n\n## Editorial reading and design relationships\n\n' + row['reading'] + '\n\n## Further reading\n\n'
    for g in row['guides']:
        reason = APPLICATION_REASONS[key] if g == 'design-expression' else 'compare related designs within this topic.'
        s += f'- [{GUIDES[g]}](../guides/{g}.md): {reason}\n'
    for other, reason in row['related']:
        s += f'- [{TITLES[other]}]({target(other)}): {reason}\n'
    return s + '\n'

manifest = {
    'schema_version': 2, 'assembled_on': '2026-10-29', 'working_language': 'en',
    'language_scope': 'All working prose, navigation, editorial relationships, and instructions are English. Original source files remain unchanged in their original languages.',
    'purpose': 'English knowledge edition with approved design-application guidance and conditional Bernini style-expression experience; no Planner runtime implementation.',
    'plan': 'docs/skill-reorganization-plan.md',
    'entries': [], 'domain_references': [], 'supporting_sources': [],
}
catalog = {'base': [], 'opuscar': [], 'domains': []}
for r in records:
    key = f"{r['no']:03d}"
    ed = editorials[key]
    path, index, template = templates[key]
    p = OUT / 'entries' / (slug(key) + '.md')
    s = front(key) + '## Complete source material in English\n\n'
    s += ('The following is the preserved English original from OPUSCAR. Clawd, the orange identity color, and handoffs to neighboring films serve its anthology. '
          'Colors, actions, timings, and Avoid clauses belong to this case. The original project used code-based drawing and 3D rendering; these records do not establish per-case Bernini results. '
          'The complete bilingual record remains available at the source link below.\n\n')
    s += f"![Original reference frame for {r['title_en']}](../../zyx/{r['frame']})\n\n"
    metadata = {k: r[k] for k in ('no', 'year', 'title_en', 'decade', 'kind', 'tone', 't0_seconds', 'duration_seconds', 'style_en', 'frame')}
    s += '### Original identifiers and segment position\n\n```json\n' + dump(metadata) + '\n```\n\n'
    s += '### Ingredients\n\n' + '\n'.join('- ' + x for x in r['blend_en']) + '\n\n'
    for field, label in [('desc_en', "Original author's design explanation"), ('prompt_en', 'Complete original style prompt')]:
        s += f'### {label}\n\n{r[field]}\n\n'
    s += '### All shots in their original order\n\n'
    for i, shot in enumerate(r['shots'], 1):
        s += f"#### {i}. {shot['name']} | {shot['seconds']} seconds\n\n{shot['text_en']}\n\n"
    s += f"### Direction and handoff\n\n{r['direction_en']}\n\n### References named by the author\n\n{r['references']}\n\n"
    s += ('The named artists, filmmakers, and works are the original author\'s reference statements; they were not individually verified through external historical research in this reorganization.\n\n'
          '## How the legacy template represents this material\n\n'
          'The converter allocated selected sentences to fixed fields by keywords, usually retaining the longest sentence in each field. Camera, editing, timing, and unassigned material went into notes. '
          'Read those fragments with the complete design above. Default risk fields such as `identity_risk`, and `common_failure_modes` derived from Avoid clauses, are converter annotations or author advice rather than measured failure records.\n\n'
          '<details>\n<summary>Complete legacy template data, unchanged</summary>\n\n```json\n' + dump(template) + '\n```\n\n</details>\n\n')
    s += (f"## Source trail\n\n- [Complete bilingual source collection](../../zyx/styles.json): select `no = {r['no']}`.\n"
          f"- [Legacy template](../../{path.relative_to(ROOT).as_posix()}): `SKILLS[{index}]`, `{template['strategy_id']}`.\n"
          '- [Original project description](../../zyx/README.md) · [Saved source page](../../zyx/opuscar98/index.html).\n'
          '- [Legacy converter](../../scripts/build_opuscar_templates.py) · [Machine-readable provenance](../source-map.json).\n')
    p.write_text(s)
    manifest['entries'].append({'id': slug(key), 'title': TITLES[key], 'path': p.relative_to(ROOT).as_posix(), 'type': 'opuscar_complete',
        'working_language': 'en', 'source': source(ROOT / 'zyx/styles.json', {'no': r['no']}), 'record_sha256': object_digest(r),
        'template': source(path, {'SKILLS_index': index, 'strategy_id': template['strategy_id']}), 'image': source(ROOT / 'zyx' / r['frame']),
        'shots': len(r['shots']), 'original_fields': list(r), 'source_presentation': 'English originals in the working page; complete bilingual record at source',
        'guides': ed['guides'], 'related': [{'id': slug(k), 'reason': reason} for k, reason in ed['related']],
        'editorial_status': 'repository-source synthesis; no new generation evidence'})
    catalog['opuscar'].append([key, TITLES[key], ed['summary']])

for key in sorted(k for k in templates if k.startswith('base-')):
    path, index, original = templates[key]
    ed = editorials[key]
    changes = translations.get(original['strategy_id'], {})
    translated = {**original, **changes}
    p = OUT / 'entries' / (key + '.md')
    s = front(key) + '## Complete base-template reading edition\n\n'
    s += ('This is an existing design proposal. Its replacements, materials, and preservation clauses are retained as source content. '
          'The record has no accompanying shot list, reference image, or item-specific experimental evidence. Its world assumptions can be compared and developed through the related cases.\n\n')
    if changes:
        s += ('The source contains Chinese prose. The complete record below translates those values into English for reading; field keys, identifiers, and already-English values are preserved. '
              'This is an attributed translation, not a modified runtime template. The exact original remains at the source link.\n\n')
    else:
        s += 'All values below are preserved from the English source.\n\n'
    s += '```json\n' + dump(translated) + '\n```\n\n'
    s += f"## Source trail\n\n- [Original template](../../{path.relative_to(ROOT).as_posix()}): `SKILLS[{index}]`, `{original['strategy_id']}`.\n"
    s += '- [Provenance](../source-map.json) · [Base-template coverage and gaps](../README.md#base-templates).\n'
    p.write_text(s)
    manifest['entries'].append({'id': key, 'title': TITLES[key], 'path': p.relative_to(ROOT).as_posix(), 'type': 'base_template_complete',
        'working_language': 'en', 'source': source(path, {'SKILLS_index': index, 'strategy_id': original['strategy_id']}),
        'record_sha256': object_digest(original), 'reading_edition_sha256': object_digest(translated),
        'translated_fields': list(changes), 'source_presentation': 'English translation with unchanged original linked' if changes else 'English original unchanged',
        'guides': ed['guides'], 'related': [{'id': slug(k), 'reason': reason} for k, reason in ed['related']],
        'editorial_status': 'repository-source synthesis; no new generation evidence'})
    catalog['base'].append([key, TITLES[key], ed['summary']])

card_path = ROOT / 'scripts/eval/bench_v3/skills_v3.py'
spec = importlib.util.spec_from_file_location('knowledge_english_cards', card_path)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
for key, card in m.CARDS.items():
    ed = editorials['domain-' + key]
    p = OUT / 'domain-references' / (key + '.md')
    s = front('domain-' + key) + '## Original experimental context\n\n'
    s += ('This card comes from the bench_v3 edit-specification writing experiments. Its source comments identify invented detail on invisible carriers, under-editing with long prompts, and target drift caused by added vocabulary. '
          'The 90-English-word advice, one-change clauses, preservation lists, and replacement directions belong to that context. '
          'The comments report 36% unknowable detail, change values of 0.21 to 0.17 to 0.12, and a 0.06 GT decline for a vocabulary variant. '
          'These remain attributed historical statements, not newly recomputed results. See the [experience synthesis](../guides/experience.md).\n\n')
    s += '## Complete original structured card\n\n```json\n' + dump(dataclasses.asdict(card)) + '\n```\n\n'
    s += '## Three complete versions supplied to the writer\n\n'
    m.route = lambda _, selected=key: selected
    for label, options in [('Base card', {}), ('Decisive: stronger replacement on relevant visible carriers', {'decisive': True}), ('Execution only: elaborate only requested content', {'execution_only': True})]:
        s += f'<details>\n<summary>{label}, original wording</summary>\n\n```text\n{m.card_block("", **options)}\n```\n\n</details>\n\n'
    s += (f'## Source trail\n\n- [Original cards, shared guidance, and routing](../../scripts/eval/bench_v3/skills_v3.py): `CARDS["{key}"]`, `_COMMON_PRIORS`, `DECISIVE_PRIORS`, and `card_block`.\n'
          '- [Experiment configuration](../../scripts/eval/bench_v3/README.md) · [Provenance](../source-map.json).\n\n'
          'The legacy router uses the first keyword match. These domain entrances support reading and comparison across domains. Future access is described in [INTEGRATION](../INTEGRATION.md).\n')
    p.write_text(s)
    manifest['domain_references'].append({'id': 'domain-' + key, 'title': ed['title'], 'path': p.relative_to(ROOT).as_posix(), 'working_language': 'en',
        'source': source(card_path, {'CARDS_key': key}), 'record_sha256': object_digest(dataclasses.asdict(card)),
        'preserved_variants': ['base', 'decisive', 'execution_only'], 'guides': ed['guides'],
        'related': [{'id': slug(k), 'reason': reason} for k, reason in ed['related']]})
    catalog['domains'].append([key, ed['title'], ed['summary']])

for filename, purpose in [
    ('zyx/README.md', 'Original project, data fields, and production method'),
    ('zyx/opuscar98/index.html', 'Locally saved complete source page'),
    ('scripts/build_opuscar_templates.py', 'Historical conversion of 98 source records into templates'),
    ('src/skills/dimensions.py', 'Context for legacy dimensions, keywords, preservation rules, and strengths'),
    ('LESSONS.md', 'Historical evaluation, input controls, and corrections to interpretation'),
    ('_deprecated/eval/bench_v2/HANDOFF.md', 'v1/v2 approaches, budgets, truncation, and task settings'),
    ('_deprecated/eval/bench_v2/data/walkthrough_notes.json', 'Repository analysis of three cases and their prompt changes'),
    ('scripts/eval/bench_v3/README.md', 'Models, tasks, input arms, references, and evaluation settings'),
    ('scripts/bench_v4/README.md', 'Historical motivation and conditional results for deterministic compilation'),
]:
    manifest['supporting_sources'].append({**source(ROOT / filename), 'use': purpose})
manifest['guides'] = [{'id': k, 'title': v, 'path': f'knowledge/guides/{k}.md'} for k, v in GUIDES.items()]
probe = ROOT / 'out/prompt_probe/20261029_bernini'
probe_cases = json.loads((probe / 'cases.json').read_text())
experience = {
    'id': 'bernini-r-20261029', 'path': 'knowledge/model-experience/bernini-r.md',
    'title': 'Bernini-R: concrete style expression in the October 29 probe',
    'working_language': 'en', 'model': probe_cases['model'], 'model_revision': probe_cases['model_revision'],
    'status': 'synthesis of existing exploratory results; no new generation',
    'scope': 'conditional style-expression experience; semantic-preservation strategies deferred',
    'sources': [], 'conditions': [],
}
for filename in ['cases.json', 'preflight.json', 'comparison.html', 'review_notes.json', 'run-summary.json',
                 'local-output-verification.json', 'evaluation-provenance.json', 'frame-mapping-audit.json', '041-paired-review.json']:
    experience['sources'].append(source(probe / filename))
for filename in ['scripts/deploy/run_prompt_probe.py', 'scripts/deploy/judge_prompt_probe.py']:
    experience['sources'].append(source(ROOT / filename))
for case in probe_cases['cases']:
    directory = probe / case['case_id']
    result = json.loads((directory / 'result.json').read_text())
    experience['conditions'].append({
        'id': case['case_id'], 'condition': case['condition'],
        'source_video': {'path': case['source_video'], 'sha256': case['source_video_sha256']},
        'input': source(directory / 'input.json'), 'result': source(directory / 'result.json'),
        'judgment': source(directory / 'judgment.json'),
        'output_video': {'path': (directory / 'edited.mp4').relative_to(ROOT).as_posix(), 'sha256': result['output_sha256']},
    })
manifest['model_experience'] = [experience]
manifest['totals'] = {'complete_entries': 111, 'opuscar_records': 98, 'base_templates': 13, 'domain_cards': 5,
    'original_shots': sum(len(r['shots']) for r in records), 'reference_images': 98, 'guides': len(GUIDES), 'model_experience_records': 1}
assert len(templates) == 111 and len(editorials) == 116
(OUT / 'source-map.json').write_text(dump(manifest) + '\n')
(WORK / 'catalog.json').write_text(dump(catalog) + '\n')
print(dump(manifest['totals']))
