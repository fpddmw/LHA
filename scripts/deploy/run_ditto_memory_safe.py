"""Run the unchanged Ditto renderer with memory-mapped T5 checkpoint storage."""
import json
import os
from pathlib import Path
import runpy
import sys
import time

ROOT=Path(__file__).resolve().parents[2]


def main():
    import torch
    manifest=Path(sys.argv[sys.argv.index('--manifest')+1]).resolve()
    target=(ROOT/'models/Wan2.1-VACE-14B/models_t5_umt5-xxl-enc-bf16.pth').resolve()
    original_load=torch.load
    events=[]
    def mapped_load(file,*args,**kwargs):
        if isinstance(file,(str,os.PathLike)) and Path(file).resolve()==target:
            kwargs.setdefault('mmap',True)
            events.append({'checkpoint':str(target),'mmap':kwargs['mmap'],
                'map_location':str(kwargs.get('map_location')),'weights_only':kwargs.get('weights_only'),
                'time':time.time(),'weights_dtype_or_values_modified':False})
            (manifest.parent/'loader-adapter-runtime.json').write_text(json.dumps({
                'adapter':'T5 memory-mapped storage only; original renderer, model files, tensor dtypes and inference settings retained',
                'events':events},indent=2))
            print(json.dumps({'stage':'memory_mapped_t5_checkpoint','mmap':kwargs['mmap']}),flush=True)
        return original_load(file,*args,**kwargs)
    torch.load=mapped_load
    runpy.run_path(str(ROOT/'scripts/deploy/run_ditto_prompt_probe.py'),run_name='__main__')


if __name__=='__main__':main()
