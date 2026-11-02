"""Frozen source-cluster analysis for planned test comparisons (no model calls)."""
from collections import defaultdict
from statistics import mean
import itertools,random

PLAN={'version':'lha-test-analysis-v3-pe-loop','primary':{'comparison':'pe-loop_final__to__none_final','endpoint':'task_completion','positive_direction':'none_final'},
      'secondary':'All other comparison/endpoint combinations, Holm within each judge',
      'population':'All planned test source groups; short/long conditions averaged within source group',
      'seed_scope':'Seed 42 only; no claim across random generation seeds',
      'missing_output':'One absent output loses administratively; both absent contribute one half. These are ITT utility assignments, not judge preferences.',
      'unknown_judge':'Both outputs available but judge unknown/transport/order-unstable gives [0,1] bounds; valid subset is auxiliary.',
      'inference':'Paired source-group sign permutation; source-cluster bootstrap; two-sided; no independent short/long or per-seed sample claims',
      'compute':'Requested, effective generations and hardware strata; equal wall limit does not establish equal compute'}


def _interval(values):
    if not values:return None
    rng=random.Random(42061102);n=len(values)
    samples=sorted(mean(rng.choices(values,k=n)) for _ in range(2000))
    return [samples[49],samples[1949]]


def _permutation(values):
    if not values:return None
    diffs=[x-.5 for x in values];observed=abs(mean(diffs));n=len(diffs)
    if n<=16:
        estimates=[abs(sum(s*d for s,d in zip(signs,diffs))/n) for signs in itertools.product((-1,1),repeat=n)]
        return sum(x>=observed-1e-12 for x in estimates)/len(estimates)
    rng=random.Random(42061102)
    estimates=[abs(sum(rng.choice((-1,1))*d for d in diffs)/n) for _ in range(10000)]
    return (1+sum(x>=observed-1e-12 for x in estimates))/(1+len(estimates))


def summarize(rows, *, population="test"):
    if population not in {"test","main","rsi"}:raise ValueError("Unknown analysis population")
    analysis_plan={**PLAN,"population":"All planned benchmark source groups"} if population=="main" else PLAN
    if population=="rsi":analysis_plan={**PLAN,"population":"RSI heldout source groups only","primary":{"comparison":"none_final__to__full_final","endpoint":"task_completion","positive_direction":"full_final"}}
    groups=defaultdict(list)
    for row in rows:
        if population=='main' or row.get('split')=='test':groups[(row['judge'],row['comparison'])].append(row)
    output={}
    for (judge,comparison),group in groups.items():
        metrics={}
        for endpoint in ('task_completion','production_quality'):
            clusters=defaultdict(list);valid=defaultdict(list);administrative=unknown=0
            for row in group:
                if row.get('seed',42)!=42:raise ValueError('This frozen analysis covers generation seed 42; use a new plan for other seeds')
                available=row.get('availability',{})
                left,right=available.get('left'),available.get('right')
                result=row.get('result')
                outcome=((result or {}).get('judgments') or {}).get(endpoint,{}).get('outcome')
                if left is False or right is False:
                    value=.5 if left is right else 1.0 if left else 0.0
                    lo=hi=value;administrative+=1
                elif outcome in {'left','right','tie'}:
                    value={'left':1.,'right':0.,'tie':.5}[outcome];lo=hi=value
                    valid[row.get('source_group',row['source_id'])].append(value)
                else:lo,hi=0.,1.;unknown+=1
                clusters[row.get('source_group',row['source_id'])].append((lo,hi))
            bounds=[(mean(p[0] for p in v),mean(p[1] for p in v)) for v in clusters.values()]
            complete=[lo for lo,hi in bounds if lo==hi]
            fully_identified=bool(bounds) and len(complete)==len(bounds)
            metrics[endpoint]={'planned_positions':len(group),'planned_source_groups':len(clusters),
                'administrative_missing_output_assignments':administrative,'judge_unresolved_positions':unknown,
                'left_itt_source_mean_bounds':[mean(v[0] for v in bounds),mean(v[1] for v in bounds)] if bounds else None,
                'left_itt_source_mean':mean(complete) if fully_identified else None,
                'source_cluster_95_ci':_interval(complete) if fully_identified else None,
                'paired_permutation_p':_permutation(complete) if fully_identified else None,
                'auxiliary_valid_source_mean':mean(mean(v) for v in valid.values()) if valid else None,
                'auxiliary_valid_source_groups':len(valid),'inference_status':'identified' if fully_identified else 'bounds_only',
                'runtime_strata':[r.get('runtime',{}) for r in group]}
        output.setdefault(judge,{})[comparison]=metrics
    for judge,comparisons in output.items():
        family=[]
        for comparison,endpoints in comparisons.items():
            for endpoint,metric in endpoints.items():
                primary=comparison==analysis_plan['primary']['comparison'] and endpoint==analysis_plan['primary']['endpoint']
                metric['role']='primary' if primary else 'secondary'
                if primary:
                    bounds=metric['left_itt_source_mean_bounds']
                    metric['none_final_preference_bounds']=[1-bounds[1],1-bounds[0]] if bounds else None
                    value=metric['left_itt_source_mean'];metric['none_final_preference']=1-value if value is not None else None
                if not primary:family.append(metric)
        # Missing p values remain members of the prespecified family with p=1.
        ordered=sorted(family,key=lambda m:m['paired_permutation_p'] if m['paired_permutation_p'] is not None else 1)
        prior=0
        for i,metric in enumerate(ordered):
            p=metric['paired_permutation_p'];prior=max(prior,min(1,(p if p is not None else 1)*(len(ordered)-i)))
            metric['holm_adjusted_p']=prior if p is not None else None
            metric['holm_family_size']=len(ordered)
    return {'plan':analysis_plan,'by_judge':output}
