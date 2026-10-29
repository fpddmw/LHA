"""Assemble authored English guides, navigation, and supporting documents."""
import json
from pathlib import Path
import re

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
K = ROOT / 'knowledge'
manifest = json.loads((K / 'source-map.json').read_text())
catalog = json.loads((WORK / 'catalog.json').read_text())


def cell(value):
    return value.replace('|', r'\|').replace('\n', ' ')


summaries = {}
for group, rows in catalog.items():
    for key, title, summary in rows:
        identity = 'opuscar-' + key if group == 'opuscar' else 'domain-' + key if group == 'domains' else key
        summaries[identity] = summary

for guide in manifest['guides']:
    body = (WORK / 'guides' / (guide['id'] + '.md')).read_text().rstrip() + '\n'
    additions = []
    for entry in manifest['entries'] + manifest['domain_references']:
        if guide['id'] not in entry['guides']:
            continue
        relative = '../' + entry['path'].removeprefix('knowledge/')
        if '](' + relative + ')' not in body:
            additions.append(f"| [{cell(entry['title'])}]({relative}) | {cell(summaries[entry['id']])} |")
    if additions:
        body += '\n## More complete material to explore\n\n'
        body += 'These entries extend the comparisons above. Each provides a complete reading edition, motivated cross-links, and source references.\n\n'
        body += '| Material | Reading orientation |\n|---|---|\n' + '\n'.join(additions) + '\n'
    (ROOT / guide['path']).write_text(body)

body = (WORK / 'README-intro.md').read_text().rstrip() + '\n'
for group, heading, folder in [('base', 'Base templates', 'entries'), ('domains', 'Domain references', 'domain-references'), ('opuscar', 'Complete OPUSCAR cases', 'entries')]:
    body += '\n## ' + heading + '\n\n| Material | Reading orientation |\n|---|---|\n'
    for key, title, summary in catalog[group]:
        stem = 'opuscar-' + key if group == 'opuscar' else key
        body += f'| [{cell(title)}]({folder}/{stem}.md) | {cell(summary)} |\n'
body += '\n## Supporting sources\n\n'
for src in manifest['supporting_sources']:
    body += f"- [{src['use']}](../{src['path']})\n"
(K / 'README.md').write_text(body)
for experience in manifest.get('model_experience', []):
    body = (WORK / 'model-experience' / Path(experience['path']).name).read_text().rstrip() + '\n\n'
    probe = ROOT / 'out/prompt_probe/20261029_bernini'
    cases = json.loads((probe / 'cases.json').read_text())['cases']
    body += '| Condition | Source | Actual input | Output and metadata | Recorded review |\n|---|---|---|---|---|\n'
    for case in cases:
        identity = case['case_id']
        base = '../../out/prompt_probe/20261029_bernini/' + identity
        body += f"| `{identity}` | [Source](../../{case['source_video']}) | [Input]({base}/input.json) | [Video]({base}/edited.mp4), [result]({base}/result.json) | [Judgment]({base}/judgment.json) |\n"
    body += '\n### Verbatim experiment prompts\n\n'
    for case in cases:
        body += f"<details>\n<summary>{case['case_id']}: original prompt</summary>\n\n```text\n{case['prompt']}\n```\n\n</details>\n\n"
    destination = ROOT / experience['path']
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(body)
for name in ['READING.md', 'INTEGRATION.md', 'VALIDATION.md']:
    (K / name).write_text((WORK / name).read_text())
for name in ['skill-reorganization-plan.md', 'skill-reorganization-discussion.md']:
    (ROOT / 'docs' / name).write_text((WORK / name).read_text())
print(f"Assembled {len(manifest['guides'])} guides, {len(manifest.get('model_experience', []))} model-experience records, the map and working documents.")

