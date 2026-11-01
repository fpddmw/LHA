"""Resident official Ditto renderer with explicit native timing and immutable receipts."""
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from evaluation.protocol import file_hash
from planner_harness.common import load, save
from planner_harness.lock import RunLock


def conditioning_indices(payload, info):
    """Source sampling is frozen per task; candidate editing keeps native frames."""
    output = payload['renderer']['output']
    count, fps = output['frames'], output['fps']
    if type(count) is not int or count < 1 or count % 4 != 1 or fps <= 0:
        raise ValueError('Invalid native frame configuration')
    if any(type(output.get(k)) is not int or output[k] <= 0 or output[k] % 16 for k in ('width','height')):
        raise ValueError('Ditto requires explicit dimensions divisible by 16')
    if payload['input_id'] == 'source':
        indices = payload['renderer'].get('conditioning_source_indices')
        if not isinstance(indices,list) or len(indices) != count:
            raise ValueError('Original source sampling must be frozen explicitly')
    else:
        if info['frames'] != count or abs(info['fps']-fps) > .001 or any(info[k] != output[k] for k in ('width','height')):
            raise ValueError('Candidate editing must preserve its native time axis and dimensions')
        indices = list(range(count))
    if any(type(i) is not int or not 0 <= i < info['frames'] for i in indices) or indices != sorted(indices):
        raise ValueError('Invalid conditioning source indices')
    return indices


class PersistentDittoRenderer:
    def __init__(self, root, config, directory):
        self.root, self.config, self.directory = Path(root), config, Path(directory)
        self.pipeline = None
        self.lock = None
        self.ready = False
        if config.get('backend') != 'ditto':
            raise ValueError('Expected Ditto configuration')
        g = config['generation']
        expected = {'num_inference_steps':50,'cfg_scale':5.0,'lora_alpha':1.0,
                    'negative_prompt':'','prompt_enhancer':False,'tiled':True,'precision':'bfloat16'}
        if g != expected:
            raise ValueError('Use the established official Ditto generation profile')

    def initialize(self):
        cfg = self.config
        manifest = Path(cfg['asset_manifest'])
        if file_hash(manifest) != cfg['asset_manifest_sha256']:
            raise ValueError('Ditto asset manifest changed')
        assets = load(manifest)
        if assets['status'] != 'complete':
            raise ValueError('Ditto asset verification incomplete')
        spec = load(self.root/'configs/ditto_models.json')
        expected = {(m['repo_id'],m['revision'],f['path']):(m,f) for m in spec['models'] for f in m['files']}
        if len(assets['files']) != len(expected):
            raise ValueError('Model inventory differs from pinned specification')
        seen = set()
        for row in assets['files']:
            path = Path(row['path'])
            matches = [(key,entry) for key,entry in expected.items() if row['repo_id']==key[0]
                       and row['revision']==key[1] and path.as_posix().endswith('/'+entry[0]['folder']+'/'+key[2])]
            if len(matches) != 1 or matches[0][0] in seen:
                raise ValueError('Unrecognized or duplicate asset')
            key,(_,entry) = matches[0];seen.add(key)
            if path.stat().st_size != entry['bytes'] or row['bytes'] != entry['bytes'] or file_hash(path) != row['sha256']:
                raise ValueError('Ditto model asset changed: '+str(path))
            if entry.get('sha256') and row['sha256'] != entry['sha256']:
                raise ValueError('Published model hash differs')
        code = Path(cfg['code_dir'])
        revision = subprocess.check_output(['git','-C',str(code),'rev-parse','HEAD'],text=True).strip()
        if revision != spec['code_revision'] or subprocess.check_output(['git','-C',str(code),'diff','--name-only','HEAD'],text=True).strip():
            raise ValueError('Official Ditto source differs from pinned revision')
        self.assets, self.spec = assets, spec
        self.code_revision = revision
        self.lock = RunLock(cfg['gpu_lock']);self.lock.__enter__()
        try:
            os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
            sys.path.insert(0,str(code))
            import torch
            from transformers import AutoTokenizer
            from diffsynth import VideoData, save_video
            from diffsynth.pipelines.wan_video_new import WanVideoPipeline, ModelConfig
            self.torch,self.VideoData,self.save_video = torch,VideoData,save_video
            self.Pipeline,self.ModelConfig = WanVideoPipeline,ModelConfig
            self.base = Path(cfg['models_root'])/'Wan2.1-VACE-14B'
            self.tokenizer=AutoTokenizer.from_pretrained(str(self.base/'google/umt5-xxl'),local_files_only=True)
            self.ready=True
        except BaseException:
            self.close();raise

    def load_pipeline(self):
        torch, ModelConfig = self.torch, self.ModelConfig
        shards=sorted(str(p) for p in self.base.glob('diffusion_pytorch_model-*.safetensors'))
        if len(shards)!=7:raise ValueError('Expected seven official model shards')
        target=(self.base/'models_t5_umt5-xxl-enc-bf16.pth').resolve()
        original=torch.load
        events=[]
        def mapped(file,*args,**kwargs):
            if isinstance(file,(str,os.PathLike)) and Path(file).resolve()==target:
                kwargs.setdefault('mmap',True)
                events.append({'path':str(target),'mmap':kwargs['mmap'],'tensor_values_or_dtype_modified':False})
            return original(file,*args,**kwargs)
        torch.load=mapped
        try:
            pipe=self.Pipeline.from_pretrained(torch_dtype=torch.bfloat16,device='cuda',
                model_configs=[ModelConfig(path=shards,offload_device='cpu'),
                    ModelConfig(path=str(target),offload_device='cpu'),
                    ModelConfig(path=str(self.base/'Wan2.1_VAE.pth'),offload_device='cpu')],
                tokenizer_config=ModelConfig(path=str(self.base/'google/umt5-xxl')),redirect_common_files=False)
        finally:
            torch.load=original
            save(self.directory/'loader-adapter-runtime.json',{'adapter':'Existing T5 memory-mapped storage precedent','events':events})
        if pipe.dit is None or pipe.vace is None:raise ValueError('Missing Ditto components')
        with redirect_stdout(io.StringIO()) as log:
            pipe.load_lora(pipe.vace,str(Path(self.config['models_root'])/'Ditto_models/models/ditto_global.safetensors'),alpha=self.config['generation']['lora_alpha'])
        text=log.getvalue();print(text,flush=True)
        match=re.search(r'(\d+) tensors are updated by LoRA',text)
        if not match or int(match.group(1)) != 80:raise ValueError('Unexpected LoRA tensor count')
        pipe.enable_vram_management()
        self.pipeline=pipe
        save(self.directory/'model-loaded.json',{'at':time.time(),'lora_updated_tensors':80,
            'asset_manifest_sha256':self.config['asset_manifest_sha256'],'torch':torch.__version__,'cuda':torch.version.cuda})

    def __call__(self,job,directory):
        payload,directory=job['payload'],Path(directory)
        cfg=payload['renderer'];g=cfg['generation'];output=cfg['output']
        if cfg['backend']!='ditto' or g != self.config['generation'] or type(cfg.get('seed')) is not int:
            raise ValueError('Task differs from resident renderer profile')
        source=Path(payload['input']['path'])
        if file_hash(source)!=payload['input']['sha256']:raise ValueError('Conditioning video changed')
        sys.path.insert(0,str(self.root/'scripts/deploy'))
        from run_prompt_probe import inspect_video
        info=inspect_video(source);indices=conditioning_indices(payload,info)
        if not self.ready:self.initialize()
        tokens=len(self.tokenizer(payload['prompt'],truncation=False,add_special_tokens=True)['input_ids'])
        if not 0<tokens<=512:raise ValueError('Prompt exceeds tokenizer limit; truncation is disabled')
        save(directory/'renderer-input.json',{'request':job,'encoded_text':payload['prompt'],
            'system_prompt':'','token_count':tokens,'conditioning_source_indices':indices})
        if self.pipeline is None:self.load_pipeline()
        video=self.VideoData(str(source),height=output['height'],width=output['width'])
        condition=[video[i] for i in indices]
        started=time.time();self.torch.cuda.reset_peak_memory_stats()
        def progress(iterable,**kwargs):
            for index,timestep in enumerate(iterable):
                yield timestep
                save(directory/'progress.json',{'step':index+1,'total_steps':g['num_inference_steps'],
                    'elapsed_seconds':time.time()-started,'updated_unix':time.time()})
        frames=self.pipeline(prompt=payload['prompt'],negative_prompt=g['negative_prompt'],vace_video=condition,
            vace_reference_image=None,height=output['height'],width=output['width'],num_frames=output['frames'],
            num_inference_steps=g['num_inference_steps'],cfg_scale=g['cfg_scale'],seed=cfg['seed'],
            tiled=g['tiled'],progress_bar_cmd=progress)
        if len(frames)!=output['frames']:raise ValueError('Generated frame count mismatch')
        native=directory/'native.mp4';self.save_video(frames,str(native),fps=output['fps'],quality=5)
        actual=inspect_video(native)
        if actual['frames']!=output['frames'] or abs(actual['fps']-output['fps'])>.001 or any(actual[k]!=output[k] for k in ('width','height')):
            raise ValueError('Generated media differs from frozen native profile')
        revisions=[{'repo_id':m['repo_id'],'revision':m['revision']} for m in self.spec['models']]
        return {'video':{'path':str(native),'sha256':file_hash(native)},'execution':{
            'backend':'ditto','requested_prompt':payload['prompt'],'effective_prompt':payload['prompt'],
            'encoded_text':payload['prompt'],'system_prompt':'','prompt_transforms':[],
            'input_sha256':payload['input']['sha256'],'conditioning_source_indices':indices,
            'input_fps':info['fps'],'output_fps':output['fps'],'settings':g,'seed':cfg['seed'],
            'model_revision':revisions,'code_revision':self.code_revision,
            'asset_manifest_sha256':self.config['asset_manifest_sha256'],'tokenizer_revision':revisions[0]['revision'],
            'token_count':tokens,'token_limit':512,'preflight':'passed','generation_seconds':time.time()-started,
            'peak_gpu_allocated_gb':self.torch.cuda.max_memory_allocated()/1e9}}

    def close(self):
        self.pipeline=None;self.ready=False
        if self.lock:self.lock.__exit__(None,None,None);self.lock=None
