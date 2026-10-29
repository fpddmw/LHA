"""Persistent full-14B Ditto loop renderer using the validated probe settings."""
import argparse
from contextlib import redirect_stdout
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from run_prompt_probe import digest, inspect_video, save

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--verified-manifest', type=Path, required=True)
    parser.add_argument('--preflight-only', action='store_true')
    args = parser.parse_args()
    run = args.run.resolve()
    assert not (run/'PAUSED.json').exists(), 'Loop is paused by the user'
    lock = (run/'worker.lock').open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    lock.seek(0); lock.truncate(); lock.write(str(os.getpid())); lock.flush()
    spec = json.loads((run/'protocol.json').read_text(encoding='utf-8'))
    models = json.loads((ROOT/'configs/ditto_models.json').read_text(encoding='utf-8'))
    verified = json.loads(args.verified_manifest.read_text(encoding='utf-8'))
    assert verified['status'] == 'complete'
    assert len(verified['files']) == sum(len(m['files']) for m in models['models'])
    for entry in verified['files']:
        assert Path(entry['path']).stat().st_size == entry['bytes'], entry['path']
    code = ROOT/'third_party/Ditto-official'
    revision = subprocess.check_output(['git','-C',str(code),'rev-parse','HEAD'],text=True).strip()
    assert revision == spec['code_revision'] == models['code_revision']
    revisions = [{'repo_id':m['repo_id'],'revision':m['revision']} for m in models['models']]
    g = spec['generation']
    assert g['num_inference_steps'] == 50 and g['precision'] == 'bfloat16'
    assert g['tiled'] and not g['prompt_enhancer']
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    sys.path.insert(0,str(code))
    import torch
    from transformers import AutoTokenizer
    from diffsynth import save_video, VideoData
    from diffsynth.pipelines.wan_video_new import WanVideoPipeline, ModelConfig
    base = ROOT/'models/Wan2.1-VACE-14B'
    tokenizer = AutoTokenizer.from_pretrained(str(base/'google/umt5-xxl'),local_files_only=True)
    pipe = None
    last_work = time.time()
    print(json.dumps({'stage':'queue_ready','pid':os.getpid(),'gpu':torch.cuda.get_device_name(0)}),flush=True)
    while not (run/'STOP').exists() and not (run/'PAUSED.json').exists():
        pending = []
        for path in sorted((run/'queue').glob('*.json')):
            req = json.loads(path.read_text(encoding='utf-8'))
            name = req['case_id']
            assert name and all(c.isalnum() or c in '_-' for c in name)
            assert req['generation'] == g
            signature = hashlib.sha256(json.dumps({'request':req,'generation':g,
                'code_revision':revision,'model_revisions':revisions},sort_keys=True).encode()).hexdigest()
            dest = run/name
            if (dest/'result.json').exists():
                prior = json.loads((dest/'result.json').read_text(encoding='utf-8'))
                assert prior['signature'] == signature
                if prior['status'] == 'complete':
                    continue
                if prior['status'] == 'failed':
                    raise RuntimeError(f'Inspect failed case before restarting: {name}')
            pending.append((req,dest,signature))
        if not pending:
            complete = [p for p in run.glob('*/result.json')
                        if json.loads(p.read_text(encoding='utf-8'))['status']=='complete']
            if len(complete) == spec['new_generations']:
                save(run/'generation-complete.json',{'status':'complete','completed_unix':time.time(),
                     'new_generations':len(complete)})
                return
            if args.preflight_only:
                return
            if time.time()-last_work > 7200:
                print(json.dumps({'stage':'idle_exit','seconds':7200}),flush=True)
                return
            time.sleep(10)
            continue
        checked = []
        for req,dest,signature in pending:
            if (run/'STOP').exists() or (run/'PAUSED.json').exists():
                return
            source = ROOT/req['source_video']
            assert digest(source) == req['source_video_sha256']
            source_info = inspect_video(source)
            indices = req['conditioning_source_indices']
            assert len(indices) == req['num_frames']
            assert min(indices) >= 0 and max(indices) < source_info['frames']
            assert req['height'] % 16 == 0 and req['width'] % 16 == 0
            if req['route'] in ('cumulative','incremental'):
                assert source_info['frames'] == req['num_frames']
                assert abs(source_info['fps']-req['fps']) < .001
                assert [source_info['width'],source_info['height']] == [req['width'],req['height']]
                assert indices == list(range(req['num_frames'])), 'Feedback must preserve its native time axis'
            tokens = len(tokenizer(req['prompt'],truncation=False,add_special_tokens=True)['input_ids'])
            assert tokens <= 512, f'{req["case_id"]}: prompt exceeds 512 tokens ({tokens})'
            checked.append({'case_id':req['case_id'],'tokens':tokens,'frames':len(indices)})
            if args.preflight_only:
                continue
            dest.mkdir(parents=True,exist_ok=True)
            save(dest/'input.json',{**req,'token_count':tokens,'system_prompt':'','effective_text':req['prompt'],
                 'source_info':source_info,'code_revision':revision,'model_revisions':revisions})
            started = time.time()
            result = {'case_id':req['case_id'],'signature':signature,'status':'running',
                      'stage':'loading' if pipe is None else 'conditioning','started_unix':started}
            save(dest/'result.json',result)
            try:
                if pipe is None:
                    shards = sorted(str(p) for p in base.glob('diffusion_pytorch_model-*.safetensors'))
                    assert len(shards) == 7
                    pipe = WanVideoPipeline.from_pretrained(torch_dtype=torch.bfloat16,device='cuda',
                        model_configs=[ModelConfig(path=shards,offload_device='cpu'),
                            ModelConfig(path=str(base/'models_t5_umt5-xxl-enc-bf16.pth'),offload_device='cpu'),
                            ModelConfig(path=str(base/'Wan2.1_VAE.pth'),offload_device='cpu')],
                        tokenizer_config=ModelConfig(path=str(base/'google/umt5-xxl')),redirect_common_files=False)
                    assert pipe.dit is not None and pipe.vace is not None
                    with redirect_stdout(io.StringIO()) as lora_log:
                        pipe.load_lora(pipe.vace,str(ROOT/'models/Ditto_models/models/ditto_global.safetensors'),alpha=g['lora_alpha'])
                    print(lora_log.getvalue(),flush=True)
                    matched = re.search(r'(\d+) tensors are updated by LoRA',lora_log.getvalue())
                    assert matched and int(matched.group(1)) == 80
                    pipe.enable_vram_management()
                    save(run/'model-loaded.json',{'status':'complete','lora_updated_tensors':80,'time':time.time(),
                        'code_revision':revision,'model_revisions':revisions,'torch':torch.__version__,'cuda':torch.version.cuda})
                video = VideoData(str(source),height=req['height'],width=req['width'])
                condition = [video[i] for i in indices]
                torch.cuda.reset_peak_memory_stats()
                inference_started = time.time()
                result.update(stage='inference',inference_started_unix=inference_started)
                save(dest/'result.json',result)
                print(json.dumps({'stage':'start','case_id':req['case_id'],'seed':req['seed'],
                      'frames':len(condition),'steps':g['num_inference_steps'],'tokens':tokens}),flush=True)
                def progress(iterable,**kwargs):
                    for index,timestep in enumerate(iterable):
                        yield timestep
                        data={'step':index+1,'total_steps':g['num_inference_steps'],
                              'elapsed_seconds':time.time()-inference_started,'updated_unix':time.time()}
                        save(dest/'progress.json',data)
                        if (index+1)%5 == 0:
                            print(json.dumps({'case_id':req['case_id'],**data}),flush=True)
                frames = pipe(prompt=req['prompt'],negative_prompt=g['negative_prompt'],vace_video=condition,
                    vace_reference_image=None,height=req['height'],width=req['width'],num_frames=req['num_frames'],
                    num_inference_steps=g['num_inference_steps'],cfg_scale=g['cfg_scale'],seed=req['seed'],
                    tiled=g['tiled'],progress_bar_cmd=progress)
                assert len(frames) == req['num_frames']
                result['stage']='saving';save(dest/'result.json',result)
                native = dest/'native.mp4'
                save_video(frames,str(native),fps=req['fps'],quality=5)
                info = inspect_video(native)
                assert info['frames']==req['num_frames'] and abs(info['fps']-req['fps'])<.001
                assert [info['width'],info['height']] == [req['width'],req['height']]
                result.update(status='complete',stage='complete',elapsed_seconds=time.time()-started,native=info,
                    native_sha256=digest(native),peak_gpu_allocated_gb=torch.cuda.max_memory_allocated()/1e9)
                save(dest/'result.json',result)
                print(json.dumps(result),flush=True)
                last_work=time.time()
            except Exception as exc:
                result.update(status='failed',elapsed_seconds=time.time()-started,error=repr(exc))
                save(dest/'result.json',result)
                raise
        if args.preflight_only:
            save(run/'preflight.json',{'status':'passed','cases':checked,'code_revision':revision,'generation':g})
            print(json.dumps({'stage':'preflight_passed','cases':checked}),flush=True)
            return


if __name__ == '__main__':
    main()
