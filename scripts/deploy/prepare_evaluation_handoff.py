"""Snapshot local experiment media for a separate evaluator; never call a judge."""
import copy
from datetime import datetime, timezone
import hashlib
from html import escape
import json
from pathlib import Path
import sys
from urllib.parse import quote

import av

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from evaluation.protocol import validate_card


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def rel(path):
    return path.relative_to(ROOT).as_posix()


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def media(path, cache):
    if str(path) not in cache:
        with av.open(str(path)) as container:
            stream = container.streams.video[0]
            times = [float(f.pts*f.time_base) for f in container.decode(video=0)]
            fps = float(stream.average_rate)
            width, height = stream.width, stream.height
        assert times and all(b>a for a,b in zip(times,times[1:])), str(path)
        zero = times[0]
        cache[str(path)] = {'sha256':sha(path), 'frames':len(times), 'fps':fps,
            'width':width, 'height':height, 'duration_seconds':len(times)/fps,
            'pts_origin_seconds':zero, 'times_seconds':[t-zero for t in times]}
    return cache[str(path)]


def main():
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    dest = ROOT/'out/evaluation_handoff'/stamp
    dest.mkdir(parents=True, exist_ok=False)
    samples = {s['sample_id']:s for s in read(ROOT/'benchmark_data/all_samples.json')}
    baseline = {m:read(ROOT/f'out/prompt_probe/20261029_{m}/cases.json') for m in ['bernini','ditto']}
    mapping_bases = {c['sample_id']:c for c in baseline['ditto']['cases']}
    tasks, rows, process, cache = {}, [], [], {}

    def task_for(sid, track):
        task_id = sid+'__'+track
        if task_id not in tasks:
            source = samples[sid]
            entry = {'protocol':'lha-evaluation-v1','task_id':task_id,'source_id':sid,
                'track':track,'split':'development','original_benchmark_split':source['split'],
                'source_video':source['source_video'],'source_sha256':source['source_video_sha256'],
                'requirement':source['prompt_'+track], 'development_exposed':True,
                'duration_seconds':133/30 if sid=='fewshot_004' else 5.0,'source_start_seconds':0,
                'annotation_status':'source_review_required','card':None}
            for cardpath in (ROOT/'examples/evaluation').glob('*.card.json'):
                card=read(cardpath)
                if card['task_id']==task_id:
                    validate_card(card)
                    assert card['source_sha256']==entry['source_sha256'] and card['requirement']==entry['requirement']
                    entry.update(card=rel(cardpath),card_sha256=card['card_sha256'],annotation_status='existing_frozen_card')
            tasks[task_id]=entry
        return tasks[task_id]

    def add(model, stage, sid, track, name, directory, seed, request=None, route=None, round_n=None):
        task=task_for(sid,track)
        cid=f'{model}__{stage}__{name}'
        result=read(directory/'result.json') if (directory/'result.json').exists() else {}
        native=directory/'native.mp4'
        available=result.get('status')=='complete' and native.exists()
        row={'case_id':cid,'model':model,'stage':stage,'source_id':sid,'task_id':task['task_id'],
             'track':track,'method':model+'__'+(route if stage=='loop' else stage+'_'+name.split('__')[-1]),
             'seed':seed,'route':route,'round':round_n,'output_video':rel(native),
             'mapping':rel(dest/'mappings'/(cid+'.json')),
             'card':task['card'] or rel(dest/'cards'/(task['task_id']+'.card.json')),
             'card_ready':bool(task['card']), 'status':'available' if available else result.get('status','pending_generation'),
             'development_exposed':True}
        if available:
            info=media(native,cache)
            expected=result['native']
            assert info['frames']==expected['frames'] and abs(info['fps']-expected['fps'])<.001
            if result.get('native_sha256'):assert info['sha256']==result['native_sha256']
            source_info=media(ROOT/task['source_video'],cache)
            assert source_info['sha256']==task['source_sha256']
            indices=mapping_bases[sid]['conditioning_source_indices']
            assert len(indices)==info['frames']
            save(dest/'mappings'/(cid+'.json'),{'source_sha256':task['source_sha256'],
                 'output_sha256':info['sha256'],
                 'source_times_seconds':[source_info['times_seconds'][i] for i in indices]})
            row.update(output_sha256=info['sha256'],frames=info['frames'],fps=info['fps'],
                       width=info['width'],height=info['height'],native_duration_seconds=info['duration_seconds'])
        inp=read(directory/'input.json') if (directory/'input.json').exists() else request or {}
        selection=read(directory/'selection.json') if (directory/'selection.json').exists() else None
        process.append({'case_id':cid,'generation_prompt':inp.get('prompt'),
            'actual_input_video':inp.get('source_video'), 'actual_input_sha256':inp.get('source_video_sha256'),
            'actual_conditioning_source_indices':inp.get('conditioning_source_indices'),
            'generation':inp.get('generation') or baseline[model]['generation'],
            'input_record':rel(directory/'input.json'),'result_record':rel(directory/'result.json'),
            'generation_seconds':result.get('elapsed_seconds'),'selection_snapshot':selection,
            'online_critic_response':rel(directory/'critic/response.json') if (directory/'critic/response.json').exists() else None,
            'planner_run':inp.get('planner_run'),'shared_r1_reused':stage=='loop_shared_r1'})
        rows.append(row)

    for model in ['bernini','ditto']:
        for case in baseline[model]['cases']:
            track='short' if case['condition']=='short' else 'long'
            add(model,'baseline',case['sample_id'],track,case['case_id'],
                ROOT/f'out/prompt_probe/20261029_{model}'/case['case_id'],case['seed'],case)
        plans=read(ROOT/f'out/planner_probe/20261029_{model}/cases.json')
        for case in plans['cases']:
            assert case['user_requirement']==samples[case['sample_id']]['prompt_'+case['task_prompt_kind']]
            add(model,'planner',case['sample_id'],case['task_prompt_kind'],case['case_id'],
                ROOT/f'out/planner_probe/20261029_{model}'/case['case_id'],case['seed'],case)
        run=ROOT/f'out/loop_probe/20261029_{model}'
        protocol=read(run/'protocol.json')
        queue={read(p)['case_id']:read(p) for p in (run/'queue').glob('*.json')}
        for task in protocol['tasks']:
            sid=task['sample_id'];track=task['user_task_type']
            assert task['user_requirement']==samples[sid]['prompt_'+track]
            add(model,'loop_shared_r1',sid,track,sid+'__shared_r1',
                (ROOT/task['shared_r1']).parent,42,task['base_case'],round_n=1)
            for route in protocol['routes']:
                for r in [2,3]:
                    name=f'{sid}__{route}__r{r}'
                    add(model,'loop',sid,track,name,run/name,41+r,queue.get(name),route,r)

    assert len(rows)==64 and len({r['case_id'] for r in rows})==64
    available=[r for r in rows if r['status']=='available']
    unique={r['output_video'] for r in available}
    ready=[r for r in available if r['card_ready']]
    minimal=lambda rr:[{k:r[k] for k in ['case_id','method','seed','card','output_video','mapping']} for r in rr]
    save(dest/'tasks.json',list(tasks.values()))
    save(dest/'all_cases.json',{'cases':rows})
    save(dest/'available_cases.json',{'cases':available})
    save(dest/'evaluate.available-with-frozen-cards.json',{'cases':minimal(ready)})
    save(dest/'baseline-planner.manifest.template.json',{'cases':minimal([r for r in rows if r['stage'] in ['baseline','planner']])})
    save(dest/'loop.manifest.template.json',{'cases':minimal([r for r in rows if r['stage'].startswith('loop')])})
    save(dest/'process_records.DO_NOT_FEED_TO_FINAL_JUDGE.json',{'records':process})
    summary={'snapshot_utc':stamp,'root_windows':str(ROOT),'root_wsl':'/home/fpddmw/projects/LHA',
        'protocol':'lha-evaluation-v1','planned_case_entries':len(rows),'available_case_entries':len(available),
        'unique_generated_videos_local':len(unique),'original_videos':4,'ready_with_frozen_cards':len(ready),
        'task_cards_missing':[t['task_id'] for t in tasks.values() if not t['card']],
        'loop_complete_local':{m:sum(r['status']=='available' and r['stage']=='loop' and r['model']==m for r in rows)
                               for m in ['bernini','ditto']},
        'generating_continues':True,'final_judgments_created':False}
    save(dest/'summary.json',summary)
    lines=['# 本地视频评价交接','',
        f'快照 UTC：{stamp}。本目录只准备媒体与对应关系，没有调用正式评价器。',
        f'本地已有 **{len(unique)} 条不同的生成视频＋4 条原片**；可评价条目 {len(available)} 个，其中包含4个复用的 loop 首轮入口。',
        '基线20条、Planner8条已完整；loop仍在生成。目录内清单是固定快照，后续新结果生成新快照。视频引用仓库内已有本地文件，无须再连服务器。','',
        '## 直接接手','',
        '- `index.html`：查看所有已回传视频与生成状态。',
        '- `tasks.json`：6个原始任务入口、源视频和原始用户指令。',
        '- `available_cases.json`：当前可用输出、SHA256、帧数、映射及任务对应。',
        '- `evaluate.available-with-frozen-cards.json`：已有冻结卡且视频完整的条目，可交新版CLI评价；这是阶段性可用子集，不是最终全量统计清单。',
        '- `baseline-planner.manifest.template.json`：完整28条基线/Planner计划。',
        '- `loop.manifest.template.json`：完整36个loop条目，包括4个复用首轮和32条新生成计划。',
        '- `all_cases.json`：上述完整64个计划条目及各自状态。未完成项保留pending/running，当前不可将它们记为生成失败。','',
        '## 评价接口和边界','',
        '路径全部相对仓库根目录。入口 `scripts/eval/evaluate_benchmark.py`，规范 `docs/evaluation-protocol.md`。',
        '现成冻结卡：041短、041长。其余任务卡尚需评价session基于原片和原始指令审阅并冻结：'+', '.join(summary['task_cards_missing'])+'。模板中的 cards 路径是明确占位，未虚构已审定标签。',
        '本批均有开发暴露；原 benchmark split 另存。新评价卡属于已有输出的回顾性评价，不能宣称生成前已冻结。',
        '使用 native.mp4：普通题101帧/20fps=5.05秒，新协议允许其作为5秒交付；乒乓球133帧/30fps≈4.43秒。',
        '每个已完成条目都有逐输出帧到原片真实PTS的映射，并绑定输入/输出哈希。loop迭代沿用实际根视频时间对应，不把变化后的画面当语义真值。',
        '041 loop 原始任务始终为短指令，虽然共享首轮使用了long_keep扩写；Planner的041/027也是短任务。不能用长任务要求评价这些输出。',
        'shared_r1是同一物理视频的复用入口；统计以源视频聚类，不能把复用、多帧或多个seed当独立视频样本。','',
        '## 过程诊断另存','',
        '`process_records.DO_NOT_FEED_TO_FINAL_JUDGE.json` 保存生成提示词、真实输入、参数、在线接受记录和耗时。独立最终judge仅使用原始要求、冻结卡与视频证据，不读取本文件、Planner扩写、旧评分或在线critic。',
        'loop在线critic继续供后续生成使用；本会话自动最终复核已关闭，正式评价交给另一个session。',
        '本目录没有预测质量分数、生成新的标准视频或改变评价协议。','']
    (dest/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    import os
    link=lambda p:quote(os.path.relpath(p,dest).replace('\\','/'))
    page='<html lang="zh"><meta charset="utf-8"><title>本地评价交接</title><style>body{font:16px/1.6 system-ui;max-width:1200px;margin:24px auto;padding:0 16px}article{border:1px solid #ccc;padding:12px;margin:12px 0}video{width:440px;max-width:100%}code{word-break:break-all}</style>'
    page+='<h1>本地评价交接</h1><p>固定快照 '+escape(stamp)+'；仅交接媒体，未打分。生成中的loop后续另出快照。</p><p><a href="README.md">交接说明</a> · <a href="available_cases.json">可用清单</a></p>'
    for task in tasks.values():
        page+='<h2>'+escape(task['task_id'])+'</h2><p>'+escape(task['requirement'])+'</p>'
        page+='<details><summary>原视频</summary><video controls muted preload="metadata" src="'+link(ROOT/task['source_video'])+'"></video></details>'
        for row in rows:
            if row['task_id']!=task['task_id']:continue
            page+='<article><b>'+escape(row['case_id'])+'</b> · '+escape(row['status'])
            if row['status']=='available':page+='<br><video controls muted preload="metadata" src="'+link(ROOT/row['output_video'])+'"></video>'
            page+='</article>'
    (dest/'index.html').write_text(page,encoding='utf-8')
    save(ROOT/'out/evaluation_handoff/latest.json',{'snapshot':rel(dest),'summary':summary})
    print(json.dumps({'snapshot':rel(dest),**summary},ensure_ascii=False),flush=True)


if __name__=='__main__':
    main()
