# Bernini / Ditto 评分交接

本交接复用当前 `lha-low-high-final-v3`，完整标准见 `docs/low-high-evaluation-v2.md`，逐档锚点见 `src/critic_harness/SCORE_DEFINITIONS.md`。不采用历史 1–4 分制，不新增加权总分。

## 评分对象与对照

75 个源视频，训练 40、验证 10、测试 25；每个方法分别生成 short/long，共 150 个输出。主结果单独报告测试集 25×2，训练与验证用于开发和校准，分别报告。评分输入为源视频、该条件下的原始提示词和最终输出；PE 扩写、Planner 计划与经验卡不充当评分要求。短提示词评分不读取对应长提示词。

Direct 和 PE 的绝对评分可独立完成。比较 Planner 提升需要同一源视频、同一原始提示词条件下的 Planner 实际输出视频；仅有 Planner 文本计划无法评价视频质量。一次规划用 planner-once，完整 RSI 用 full，无经验对照用 none。研究经验收益需要 full 与 none 的同设置结果；研究迭代收益需首轮、最终选中视频以及候选/选择记录。已有视频可直接导入，无需为评分重跑生成。

Bernini 与 Ditto 分库存储。各自 PE 对各自 Direct 衡量增强收益；跨渲染器比较同时包含渲染器差异。Ditto 只有 PE 时可以绝对评分，增强收益比较待 Ditto Direct 补齐。缺失结果保留缺失状态，不计零分。正式结果保持 short/long、裁判和方法分别汇总；同源视频重复条件按源视频宏平均。记录有效数量、失败与未知比例。

## 指标

| 指标 | 取值与含义 |
|---|---|
| IA / CP / TC / VI / AC | 0–4 整数：指令遵循、应保留内容、时间一致性、视觉完整性、审美协调；逐档使用原评分锚点 |
| 编辑完成、必要对应关系 | pass=1 / partial=0.5 / fail=0；未知单列 |
| 长提示词 | 定点绑定准确率、全部要求联合满足率 |
| 短提示词 | 风格实现、场景针对性、有效创意 0–4；相对原创性仅在固定匿名参照集存在时评价 |
| 审美细项 | 叙事情绪、风格世界一致性、构图光线、色彩质感、层次可读性；完整时才计算均值 |
| 损伤 | 非请求损伤、重大损伤分别报告 |
| 自动诊断 | CLIP-F、DINO-F、全帧光流重投影误差、运动量及低运动时长比例；按适用条件比较源动作 |
| 双向盲评 | 任务完成与成片质量分别 A/B/tie/unknown；交换顺序冲突记 order_unstable |

裁判复用 glm5.3flash 与 sonnet-5.5high。概览加连续原生帧事件证据，所有方法共用源事件边界；禁止用少数静帧替代完整时间证据。所有细则和适用性以完整标准及冻结的 profile 为准。

## 从 GitHub 获取可运行版本

本次发布目录为 `handoffs/scoring-20261102/`。下载其中的 `scoring-tools.zip` 和 `scoring-tools.zip.sha256`，与已有的 `benchmark.zip` 放在同一目录。请从同一个 GitHub 提交下载两个评分文件。GitHub 仓库其余代码可能处于不同开发阶段，本次运行入口是这个冻结快照。

以下命令面向 Linux / WSL，在保存这三个文件的目录执行：

```bash
sha256sum -c scoring-tools.zip.sha256
mkdir -p lha-scoring
unzip -q scoring-tools.zip -d lha-scoring
unzip -q benchmark.zip -d lha-scoring
cd lha-scoring
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.critic.txt -r requirements.evaluation.txt
ffmpeg -version
ffprobe -version
python scripts/import_renderer_results.py --help
python scripts/benchmark_results.py --help
```

缺少 ffmpeg 时先通过所在机器的软件包管理器安装。已有项目评分环境可以直接复用，无需新建环境。运行目录结构应为：

```text
lha-scoring/
  scripts/
  src/
  docs/
  benchmark_data/
    benchmark.json
    train/001/video.mp4
    validation/041/video.mp4
    test/051/video.mp4
```

同事传回的是生成结果目录，另行存放，例如 `/results/bernini-pe/`，其结构是 `plan.json`、`runtime.json`、`cases/<case_id>/result.json`、`input.json`、`native.mp4` 和原始追踪文件。只传视频无法走验证导入入口。

## 环境与导入

使用现有 LHA 评分环境，或 Python 3.12 环境安装：

```sh
python -m pip install -r requirements.critic.txt -r requirements.evaluation.txt
```

机器需提供 ffmpeg/ffprobe。自动特征首次使用需获取固定版本 CLIP/DINO 权重；模型 API 使用现有 `LHA_PARATERA_BASE_URL` / `LHA_PARATERA_API_KEY` 和 `LHA_SONNET_BASE_URL` / `LHA_SONNET_API_KEY`。不在包内存放密钥。将既有 benchmark.zip 解压在项目根，使 benchmark_data/benchmark.json 存在。工具包运行目录须完整保留 plan.json、runtime.json、cases/，不要只传 mp4。

```sh
python scripts/import_renderer_results.py --renderer bernini --run /results/bernini-pe --root out/scoring/bernini
python scripts/import_renderer_results.py --renderer bernini --run /results/bernini-direct --root out/scoring/bernini
python scripts/import_renderer_results.py --renderer ditto --run /results/ditto-pe-adapted-v2 --root out/scoring/ditto
python scripts/benchmark_results.py prepare-evaluation --root out/scoring/bernini --evaluation-id baseline-v1
python scripts/benchmark_results.py prepare-evaluation --root out/scoring/ditto --evaluation-id baseline-v1
```

导入校验源任务、视频和生成收据哈希；保留增强模板及运行版本身份。重跑相同导入可续接；不同生成版本使用新 collection。待生成位置保留在报告中。上述命令不调用评分模型。

## 配置评分服务

在终端设置以下变量；将示例文本替换为项目已验证的实际值，API key 不要提交 GitHub：

```bash
export LHA_PARATERA_BASE_URL='填写已验证的 HTTPS API base URL'
export LHA_PARATERA_API_KEY='填写实际密钥'
export LHA_SONNET_BASE_URL='填写已验证的 HTTPS API base URL'
export LHA_SONNET_API_KEY='填写实际密钥'
```

当前适配器分别校验 `llmapi.paratera.com` 和 `api.tu-zi.com` 主机。已有密钥环境直接沿用。真实 base URL 的路径按项目服务配置填写，不猜测接口路径。

正式执行还需要一份项目 accounting 预算配置，含实际限额、报价和能力约束。下方 `/absolute/path/approved-budget.json` 是明确的待替换路径；本包不含可直接用于付费运行的预算文件。因此可以立即完成离线导入与准备，正式评分需补齐这些运行配置。

## 正式评分与补充 Planner

```sh
python scripts/benchmark_results.py score-evaluation --root out/scoring/bernini --execute --budget-config /absolute/path/approved-budget.json
python scripts/benchmark_results.py score-evaluation --root out/scoring/ditto --execute --budget-config /absolute/path/approved-budget.json
```

budget-config 使用项目现有 accounting 策略格式与已核实报价，必须覆盖双裁判和自动指标；参照 `src/planner_harness/accounting.py`。不提供伪造预算或免费报价。每个 collection 共用其冻结账本，恢复继续累计费用。先在验证集已有结果上检查流程，再扩展；CLI 的 --split 仅筛选展示数量，**不限制 score-evaluation 执行范围**。若只评验证集，应向专用 collection 仅导入验证集结果。

Planner 使用现有通用结果清单入口：

```sh
python scripts/benchmark_results.py import --manifest /results/planner-results.json --root out/scoring/bernini
python scripts/benchmark_results.py append-evaluation --root out/scoring/bernini
python scripts/benchmark_results.py score-evaluation --root out/scoring/bernini --execute --budget-config /absolute/path/approved-budget.json
```

清单为数组，每项含 sample_id、prompt_form、method、seed、source_sha256、request（原文）、video（绝对路径）、generation（实际配置对象）、evidence（溯源对象）；可附 video_sha256。full/none 提供 candidates，使用现有 unified_benchmark 的导出记录，以保留 first/selected 角色。不要把 Bernini Planner 结果导入 Ditto 库。盲评按现有 comparison_pairs 自动运行；不是所有方法的两两全排列，所需额外配对应先确定并冻结。

结果入口为各 collection 的 index.html 和汇总文件。补齐结果采用 append，不覆盖旧评分；评分协议或裁判身份变化时创建新 evaluation-id。

## 交付方式

建议 GitHub 固定提交版本作为长期入口，ZIP 用作当前可传输快照。当前 ZIP 是工作区代码快照（逐文件 SHA256），不宣称已推送 GitHub。包含评分代码、标准与 benchmark 清单；视频使用原 benchmark.zip，不重复打包权重、视频、密钥和历史运行结果。本轮只准备与离线验证，没有实际模型评分，也没有生成评分结论。

## 查看结果、续跑和验证范围

```bash
python scripts/benchmark_results.py report --root out/scoring/bernini
python scripts/benchmark_results.py report --root out/scoring/ditto
```

用浏览器打开各自 `index.html`；机器可读结果是同目录 `results.json`。`ready` 表示视频已导入，评分是否完成另看 `evaluation_status` 和各裁判记录。所有原始请求、回答、费用和自动指标保存在对应 evaluation 目录中。

断点续跑再次执行相同的 `score-evaluation` 命令，不要重新运行同名 `prepare-evaluation`。迟到视频先重复导入，再 append，然后续跑。原始输入或生成版本变化时换 collection；评分协议变化时换 evaluation-id。不要删除失败记录来伪装成功。

本次离线验证：新增导入测试 3 项、现有结果登记测试 8 项、评分专项测试 11 项通过。更广的生成流程测试另有 2 项未通过，涉及 Planner 夹具缺少知识 manifest 以及迟到结果恢复预期；本交接不宣称生成流程全量测试通过。没有调用在线裁判、运行真实特征模型或产出正式评分结果。

本包不会生成 Direct、PE 或 Planner 视频；生成仍用已交接的 Bernini / Ditto 生成工具包。评分接收它们的实际产物。当前具备 Bernini Direct+PE 时可以比较增强收益；Ditto 仅有 PE 时先做绝对评分。完整 Planner/RSI 对照的输入要求见前文。
