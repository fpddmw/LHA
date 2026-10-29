"""Persistent Bernini renderer for explicit, auditable loop requests.

The controller supplies prompts and accepted-parent choices; no legacy planner.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from run_prompt_probe import digest, inspect_video, save

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    args = p.parse_args()
    run = args.run.resolve()
    run.mkdir(parents=True, exist_ok=True)
    if (run / 'PAUSED.json').exists():
        raise RuntimeError('This loop is paused by the user; explicit resume authorization is required.')
    lock = (run / 'worker.lock').open('w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    lock.write(str(os.getpid())); lock.flush()
    sys.path.insert(0, str(ROOT / 'third_party/Bernini'))
    import torch
    from transformers import AutoTokenizer
    from bernini.cli import add_common_args, build_pipeline, generation_kwargs, resolve_system_prompt
    from bernini.pipeline import _prompt_clean
    from bernini.data_utils import VideoFrameReader, smart_video_nframes
    spec = json.loads((run / 'protocol.json').read_text())
    model_dir = ROOT / 'models/Bernini-R-1.3B-Diffusers'
    cli = add_common_args(argparse.ArgumentParser()).parse_args([
        '--config', str(model_dir), '--task_type', 'v2v', '--guidance_mode', 'v2v_apg',
        '--num_inference_steps', '40', '--max_image_size', '848', '--neg_prompt', '',
    ])
    prefix = resolve_system_prompt({'task_type': 'v2v'}, cli)
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir), subfolder='tokenizer', local_files_only=True)
    pipeline = None
    last_work = time.time()
    print(json.dumps({'stage': 'queue_ready', 'pid': os.getpid(), 'gpu': torch.cuda.get_device_name(0)}), flush=True)
    while not (run / 'STOP').exists():
        pending = []
        for path in sorted((run / 'queue').glob('*.json')):
            req = json.loads(path.read_text(encoding='utf-8'))
            name = req['case_id']
            assert name and all(c.isalnum() or c in '_-' for c in name)
            dest = run / name
            signature = hashlib.sha256(json.dumps(req, sort_keys=True).encode()).hexdigest()
            target = dest / 'result.json'
            if target.exists():
                result = json.loads(target.read_text())
                assert result['signature'] == signature
                if result['status'] == 'complete':
                    continue
                if result['status'] == 'failed':
                    raise RuntimeError(f'Inspect failed case before restarting: {name}')
            pending.append((req, dest, signature))
        if not pending:
            completed = list(run.glob('*/result.json'))
            if len(completed) >= spec['new_generations']:
                save(run / 'generation-complete.json', {'completed_unix': time.time(), 'new_generations': len(completed)})
                break
            if time.time() - last_work > 7200:
                print(json.dumps({'stage': 'idle_exit', 'seconds': 7200}), flush=True)
                break
            time.sleep(10)
            continue
        for req, dest, signature in pending:
            dest.mkdir(exist_ok=True)
            source = ROOT / req['source_video']
            assert digest(source) == req['source_video_sha256']
            source_info = inspect_video(source)
            if req['route'] in ('cumulative', 'incremental'):
                assert source_info['frames'] == req['num_frames']
                assert abs(source_info['fps'] - req['fps']) < .001
            tokens = tokenizer(prefix + _prompt_clean(req['prompt']), truncation=False)['input_ids']
            if len(tokens) > 512:
                raise ValueError(f'{req["case_id"]}: token count {len(tokens)} exceeds 512')
            reader = VideoFrameReader(str(source))
            indices = smart_video_nframes(reader.length, reader.fps, req['fps'], frame_factor=4,
                                          max_frames=req['num_frames'], add_one=True)
            assert len(indices) == req['num_frames']
            if req['route'] in ('cumulative', 'incremental'):
                assert indices == list(range(req['num_frames'])), 'Feedback resamples the time axis'
            save(dest / 'input.json', {**req, 'system_prompt': prefix, 'token_count': len(tokens),
                'conditioning_source_indices': indices, 'source_info': source_info})
            if pipeline is None:
                pipeline = build_pipeline(cli, torch.device('cuda:0'))
                save(run / 'model-loaded.json', {'time': time.time(), 'gpu': torch.cuda.get_device_name(0),
                     'torch': torch.__version__, 'cuda': torch.version.cuda, 'config_sha256': digest(model_dir/'config.json')})
            started = time.time()
            result = {'case_id': req['case_id'], 'signature': signature, 'status': 'running', 'started_unix': started}
            save(dest / 'result.json', result)
            print(json.dumps({'stage': 'start', 'case_id': req['case_id'], 'seed': req['seed']}), flush=True)
            try:
                options = generation_kwargs(cli)
                options.update(num_frames=req['num_frames'], fps=req['fps'], seed=req['seed'])
                pipeline(req['prompt'], video=str(source), output_path=str(dest/'native.mp4'), system_prompt=prefix, **options)
                info = inspect_video(dest/'native.mp4')
                assert info['frames'] == req['num_frames'] and abs(info['fps']-req['fps']) < .001
                # Native outputs are retained for feedback; no packet-copy truncation.
                result.update(status='complete', elapsed_seconds=time.time()-started, native=info,
                              native_sha256=digest(dest/'native.mp4'))
                save(dest/'result.json', result)
                print(json.dumps(result), flush=True)
                last_work = time.time()
            except Exception as exc:
                result.update(status='failed', error=str(exc), elapsed_seconds=time.time()-started)
                save(dest/'result.json', result)
                raise


if __name__ == '__main__':
    main()
