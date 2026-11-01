"""Hash-bound supplemental review of an explicitly reviewed descriptive false positive."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from critic_harness.one_shot import frozen_profile, validate_report
from evaluation.creative import judge_identity
from experiments.creative_fewshot import cache_judgment as native_cache
from planner_harness.common import load, sha
from planner_harness.execution import immutable, signature
from planner_harness.lock import RunLock

SENTENCE = ('The request does not state whether the basketball hoop should be removed, '
            'so its retention is treated as an ambiguity rather than a clear violation.')
FIELD = ['main_scores','instruction_adherence','limitations',2]
ERROR = 'Critic output contains prohibited action guidance'


def binding_for(root, topic, video, name):
    return {'request':topic['request'],'source':topic['source_sha256'],'candidate':video['sha256'],
            'protocol':frozen_profile()['sha256'],**judge_identity(name),
            'adapter':sha(Path(root)/'src/evaluation/creative.py')}


def review_binding(directory):
    """Collect immutable evidence for a human/independent-agent review record."""
    directory=Path(directory)
    return {'identity':load(directory/'identity.json'),
            'response_sha256':sha(directory/'call/response.txt'),
            'evidence_packet_sha256':sha(directory/'evidence/request.json'),
            'model_input_sha256':sha(directory/'call/input.json'),
            'original_rejection_sha256':sha(directory/'invalid-report.json'),
            'frozen_validator_sha256':frozen_profile()['implementation_sha256']['review']}


def revalidate(directory, review, binding):
    directory=Path(directory)
    if review.get('schema')!='lha-supplemental-descriptive-review-v1' or review.get('disposition')!='descriptive_false_positive':
        raise ValueError('Unrecognized supplemental review disposition')
    if review.get('review_kind')!='agent independent review' or not review.get('reviewer_thread'):
        raise ValueError('Supplemental review requires explicit independent-review provenance')
    if review.get('field')!=FIELD or review.get('original_sentence')!=SENTENCE or review.get('exempted_match')!='should':
        raise ValueError('The reviewed field, sentence and exact match differ')
    if review.get('binding')!=review_binding(directory) or review['binding']['identity']!=binding:
        raise ValueError('Supplemental review evidence or identity changed')
    raw=(directory/'call/response.txt').read_text().strip()
    if raw.startswith('```json\n') and raw.endswith('```'):raw=raw[8:-3].strip()
    report=json.loads(raw)
    cursor=report
    for key in FIELD:cursor=cursor[key]
    if cursor!=SENTENCE:
        raise ValueError('Original report field differs from the reviewed sentence')
    try:
        validate_report(report,load(directory/'evidence/request.json'))
    except ValueError as exc:
        if str(exc)!=ERROR:raise ValueError('Original frozen rejection differs') from exc
    else:
        raise ValueError('Original frozen advice rejection was not reproduced')
    projected=copy.deepcopy(report)
    projected['main_scores']['instruction_adherence']['limitations'][2]=SENTENCE.replace('should','[independently reviewed descriptive modal]')
    validate_report(projected,load(directory/'evidence/request.json'))
    for frame in load(directory/'evidence/request.json')['images']:
        if sha(frame['path'])!=frame['sha256']:
            raise ValueError('Supplemental review evidence image changed')
    return report


def cache_judgment(root, output, topic, video, *, name='glm5.3flash', judge=None):
    binding=binding_for(root,topic,video,name)
    key=signature(binding);directory=Path(output)/'final-judge'/key
    review_path=directory/'supplemental-review/review.json'
    if not review_path.exists():
        return {**native_cache(root,output,topic,video,name=name,judge=judge),
                'validation_status':'native_passed'}
    with RunLock(directory):
        if load(directory/'identity.json')!=binding or sha(Path(root)/topic['source'])!=binding['source'] or sha(video['path'])!=binding['candidate']:
            raise ValueError('Supplemental judgment identity/media mismatch')
        review=load(review_path)
        report=revalidate(directory,review,binding)
        status={'status':'supplemental_review_passed','review_kind':'agent independent review',
                'review_path':str(review_path),'review_sha256':sha(review_path),
                'original_validator_result':ERROR,'original_rejection_retained':True,
                'original_response_sha256':review['binding']['response_sha256'],
                'exact_field':FIELD,'exact_exempted_match':'should',
                'validation_copy_only':'Only the exact reviewed descriptive modal is masked for validation; stored report retains full original text.',
                'other_frozen_checks':'passed','model_calls_added':0,
                'adapter_sha256':sha(Path(__file__))}
        immutable(directory/'supplemental-review/validation.json',status)
        result={'usage':'independent_final',**judge_identity(name),'source_sha256':binding['source'],
                'output_sha256':binding['candidate'],'profile_sha256':binding['protocol'],
                'report':report,'request_path':str(directory/'evidence/request.json'),'validation':status}
        immutable(directory/'judgment.json',result)
        return {'key':key,'path':str(directory/'judgment.json'),'sha256':sha(directory/'judgment.json'),
                'result':result,'validation_status':'supplemental_review_passed'}
