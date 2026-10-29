"""Measure each exact ablation prompt with its real renderer tokenizer, without loading weights."""
import argparse,json,sys
from pathlib import Path
from run_prompt_probe import ROOT,digest,save


def main():
    p=argparse.ArgumentParser();p.add_argument('--renderer',choices=['bernini','ditto'],required=True)
    p.add_argument('--manifest',type=Path,required=True);args=p.parse_args()
    manifest=args.manifest.resolve();spec=json.loads(manifest.read_text(encoding='utf-8'))
    from transformers import AutoTokenizer
    if args.renderer=='ditto':
        tokenizer=AutoTokenizer.from_pretrained(str(ROOT/'models/Wan2.1-VACE-14B/google/umt5-xxl'),local_files_only=True)
        effective=lambda text:text
    else:
        sys.path.insert(0,str(ROOT/'third_party/Bernini'))
        from bernini.cli import add_common_args,resolve_system_prompt
        from bernini.pipeline import _prompt_clean
        model=ROOT/'models/Bernini-R-1.3B-Diffusers';g=spec['generation']
        cli=add_common_args(argparse.ArgumentParser()).parse_args(['--config',str(model),'--task_type','v2v',
            '--guidance_mode',g['guidance_mode'],'--num_inference_steps',str(g['num_inference_steps']),
            '--max_image_size',str(g['max_image_size']),'--neg_prompt',g['negative_prompt']])
        prefix=resolve_system_prompt({'task_type':'v2v'},cli)
        tokenizer=AutoTokenizer.from_pretrained(str(model),subfolder='tokenizer',local_files_only=True)
        effective=lambda text:prefix+_prompt_clean(text)
    receipts=[]
    for c in spec['cases']:
        assert digest(ROOT/c['source_video'])==c['source_video_sha256']
        assert __import__('hashlib').sha256(c['prompt'].encode()).hexdigest()==spec['submitted_prompt_sha256'][c['case_id']]
        count=len(tokenizer(effective(c['prompt']),truncation=False,add_special_tokens=True)['input_ids'])
        receipts.append({'case_id':c['case_id'],'tokens':count,'limit':512,'passed':count<=512,
            'raw_prompt_sha256':c['planner_prompt_sha256'],'effective_text':effective(c['prompt'])})
    save(manifest.parent/'token-preflight.json',{'renderer':args.renderer,'manifest_sha256':digest(manifest),
        'planning_terminal':spec['planning_terminal'],'cases':receipts,'truncation':False,'prompt_rewriting':False})
    print(json.dumps({'renderer':args.renderer,'token_counts':{r['case_id']:r['tokens'] for r in receipts},
                     'failed':[r['case_id'] for r in receipts if not r['passed']]}),flush=True)


if __name__=='__main__':main()
