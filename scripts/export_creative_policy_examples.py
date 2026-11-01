"""Export exact mocked-model inputs and decisions; no real model, renderer or improvement claim."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,required=True,help='New local software-fixture run directory')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();work=args.work.resolve();output=args.output.resolve()
    if work.exists():raise ValueError('Use a new fixture directory; retain existing example runs')
    work.mkdir(parents=True);output.mkdir(parents=True,exist_ok=True)
    import cv2
    import numpy as np
    from test_creative_loop import Scripted,ScriptedCritic,action
    from planner_harness import PlannerHarness
    from planner_harness.common import load,save,sha
    from planner_harness.execution import collect
    from planner_harness.delivery import verify_delivery
    from critic_harness.adapter import critique
    source=work/'software-source.avi'
    writer=cv2.VideoWriter(str(source),cv2.VideoWriter_fourcc(*'MJPG'),10,(80,60))
    for i in range(20):writer.write(np.full((60,80,3),i*10,dtype=np.uint8))
    writer.release();run=work/'run'
    h=PlannerHarness(run,Scripted([action('generate',input_video='source',prompt='Render the scene in a soft blue palette.')]))
    h.start(source,'Make the scene blue.',mode='loop',workflow='creative_loop_v1',execution={'mode':'replay'})
    def render_receipt():
        job=h.state['jobs'][h.state['pending_tool']];p=job['payload']
        save(run/'jobs'/job['id']/'response.json',{'request_sha256':job['sha256'],'mode':'replay','status':'complete',
            'payload':{'video':{'path':str(source),'sha256':sha(source)},'replay_provenance':'CPU synthetic software example, no real generation.',
                'execution':{'requested_prompt':p['prompt'],'effective_prompt':p['prompt'],'input_sha256':p['input']['sha256'],
                             'generation_seconds':1.0,'cost_provenance':'Synthetic example value; not measured GPU/model cost.'}}})
        collect(h)
    def resume(actions):
        nonlocal h
        h.checkpoint();h=PlannerHarness(run,Scripted(actions));h.resume()
    render_receipt();resume([action('generate',input_video='source',prompt='Use blue pigment while retaining the original framing.')]);render_receipt()
    resume([action('generate',input_video='v2',prompt='Render cleaner blue contours while preserving the scene layout.',
        justification='v2 is the most suitable retained candidate in this software example; contour clarity remains the question. I will use v2 to test cleaner blue contours while preserving its layout, rather than resampling from the source. This attempt is intended to establish whether that change warrants another render instead of entering delivery confirmation now.')])
    generate_event=h.state['jobs'][h.state['pending_tool']]['id'].removesuffix('-generate')
    render_receipt();resume([action('critique',video='v1',compare_to='v2',focus='Inspect visible geometry.',extra_checks=['Is source framing preserved?'])])
    job=h.state['jobs'][h.state['pending_tool']];folder=run/'jobs'/job['id'];critic=ScriptedCritic()
    feedback=critique(job,folder,ROOT,model=critic)
    save(folder/'response.json',{'request_sha256':job['sha256'],'mode':'replay','status':'complete','payload':feedback})
    resume([action('finish',video='v1',message='Propose the retained candidate with its stated limitations.'),
            action('finish',video='v1',message='Confirm this software-example delivery after the complete reused report; retain its uncertainty.')])
    verify_delivery(run);proof=h.state['final']['delivery_review']
    if proof['review_origin']!='reused' or len(critic.inputs)!=1:raise ValueError('Expected cached-report confirmation with no additional Critic call')
    files={'initial-model-input.json':run/'calls/event-0001/input.json',
           'continuation-model-input.json':run/'calls'/generate_event/'input.json',
           'accepted-generate.json':run/'calls'/generate_event/'response.txt',
           'cached-report-confirmation-input.json':run/'calls'/proof['planner_event_id']/'input.json'}
    for name,path in files.items():shutil.copyfile(path,output/name)
    save(output/'cached-report-confirmation-proof.json',proof)
    manifest={'scope':'Software examples using CPU-made media and mocked models. No real model, GPU render or observed quality improvement.',
              'real_external_model_calls':0,'real_gpu_renders':0,'mocked_critic_calls':len(critic.inputs),
              'extra_critic_calls_for_delivery':0,'fixture_run':str(run),
              'files':{name:{'sha256':sha(output/name),'exact_saved_source':str(path)} for name,path in files.items()}}
    save(output/'manifest.json',manifest)
    (output/'README.md').write_text('# Software examples: continuation and informed delivery\n\n'
        'These are exact saved inputs and a response from mocked-model harness calls over CPU synthetic media. '
        'They establish software behavior, not observed model improvement. No provider API or GPU was used.\n\n'
        '- [Initial model input](initial-model-input.json): common instructions and spent facts.\n'
        '- [Continuation input](continuation-model-input.json): pre-announced questions before the next decision.\n'
        '- [Accepted generate](accepted-generate.json): input, actual prompt and free-text explanation in one response.\n'
        '- [Cached-report confirmation input](cached-report-confirmation-input.json): the complete report with its original comparisons and supplemental checks, bound to the new proposal.\n'
        '- [Confirmation proof](cached-report-confirmation-proof.json) links that input to the later finish response.\n\n'
        'The mocked Critic was invoked once during work and zero additional times for delivery. '
        'Paths identify the retained local fixture; the exported text is unmodified.\n',encoding='utf-8')
    print(json.dumps({'status':'exported_software_examples','output':str(output),'real_external_calls':0,'extra_critic_calls_for_delivery':0}))


if __name__=='__main__':main()
