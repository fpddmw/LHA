# Online generation and time budget

> 阶段记录：本文保留当时的设计、数据版本或执行状态。当前开发版以 [文档入口](README.md)、[当前状态](current-status.md) 和 [实验运行安排](experiment-campaign.md) 为准。

Current authorized protocol: 2026-11-03, `creative-resources-v2` and `creative-continuation-v4`. This replaces the earlier five-only/count-stage draft in this file. Existing frozen runs retain their recorded protocol; the current three-device Direct work is not hot-replaced.

One task is sample + short/long + method + seed. Each method has its own N submitted generation attempts (default four) and at most 9000 online seconds. The clock starts after worker/GPU readiness and stays fixed on recovery. Queueing before start is excluded; subsequent waiting is included. Planner turns, model requests and tokens are actual accounting records with no default task stopping threshold. Explicit optional money protections remain enforced when configured.

Only actual render dispatch consumes a generation slot. Failed execution counts, known unsubmitted validation does not, and collecting the original request never consumes a second slot. An unknown submission retains its original occupancy and prevents blind replacement. At N only generation is disabled. At the time deadline the result freezes, new calls stop and registered task-owned model/renderer processes are cancelled. Local stop evidence and external provider uncertainty are recorded separately. Late evidence is retained beside the original request and does not alter the settled result.

Internally p=max(submitted/N, elapsed/online_seconds). The phases are exploration below .4, continuation below .6, deliberate below .8, and strong thereafter while generation remains available. The model receives a neutral qualitative reminder and generation_available. Justification is optional at every stage; no continuation questions or delivery conditions are added. Exact limits, elapsed time, tokens and call counts stay in operator records. These thresholds extend the earlier 2/3/4-stage engineering convention; they are not an empirical optimum. There is no predicted-duration or last-minute admission rule.

`ProcessRenderer` owns a dedicated warm pipeline and host-local GPU lock. The runtime validates input/hash/token/time-axis before submitted accounting. Deadline cancellation targets its recorded child identity, never an arbitrary GPU process or shared service. Unsupported external stop remains unknown. `owned_process` and the accounting task-admission guard coordinate model-process start and cancellation.

`run_creative_benchmark.py` uses the existing unified result registry and six method adapters. Independent final judging remains separate and paused. Test-only post-task maintenance runs under its own configuration after the online batch settles. CPU/mock verification does not establish real GPU acceptance.

Historical implementation evidence for the superseded five-only policy remains under `out/creative_generation_budget/20261102/`; current implementation verification is under `out/loop_protocol_upgrade_20261102/`.
