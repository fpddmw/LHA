# Bernini seven-task delivery run

Authorized on 2026-10-31. Use the user-provided single RTX 5090 instance on AutoDL (SSH port 17191); do not rent another GPU. Run the seven original fewshot long requests through the current Wiki-enabled task-local RSI loop. Planner and online Critic both use gpt-6.1-sol with high reasoning. Freeze the Critic instructions, non-experience knowledge and model profile across all seven tasks. Critic reports outcomes/evidence and uncertainty; Planner controls input, prompt, next attempt and final selection.

No independent final scoring, encoder metrics, benchmark ablations or automatic global experience adoption. Preserve all candidate videos, exact prompts, requirements, predictions, automatic reviews, knowledge reads, ancestry, final selections, costs and failures. First reach model-led delivery on one task before admitting the remaining six. There is no fixed generation count. Resource exhaustion, an execution failure or a blocked repair leaves the task incomplete, with any selected candidate provisional.

Prepare downloads on the server; only necessary current code, knowledge and source media may travel from this workspace. Use a persistent renderer without changing the established 40-step, v2v_apg, maximum-size-848 profile, native timing, precision or prompt-enhancer settings. Large weights never transit the local VPN. Credentials remain outside repository evidence.

Transfer all results back and verify file hashes before stopping this instance. Preserve a resumable checkpoint under out/fewshot_loop/20261031. Active-job checks normally use 10–15-minute intervals. Notify substantive progress, failures needing attention, or completion. The previous scoring queues and heartbeats remain unrelated and paused.

## Correction recorded on 2026-11-01

The original launch incorrectly imposed three generations and a three-element seed list. All seven archived runs terminated for budget reasons. Their 21 videos and complete records are retained, but the seven budget stops do not satisfy the user's delivery instruction. The instance was stopped after retrieval; that shutdown used the wrong completion condition.

The active entry is scripts/deploy/run_fewshot_delivery.py. Delivery runs have null generation/turn ceilings and an arithmetic seed sequence starting at 42. The Planner chooses whether a candidate is suitable for delivery using the task and frozen Critic evidence; no all-pass Critic threshold replaces that judgment. A budget stop cannot pass verify_delivery or the batch's first-task/final delivery checks. Bounded benchmark experiments retain their explicit budgets and remain separately labeled.

An explicit --resume --continue-delivery operation can reopen a resolved historical budget stop, retaining candidates, observations, prompts, requirement versions and Critic materials. It records the configuration correction and archives the provisional final selection. Frozen validation/cycle runs cannot be converted through that operation. Do not modify the archived results directory or issue duplicate pending work. Software checks use scripted models and fixture media; they are not new Bernini generation evidence.
