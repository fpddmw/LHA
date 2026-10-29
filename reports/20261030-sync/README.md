# 2026-10-30 代码与实验同步快照

冻结时间：2026-10-29T18:43:05.118741+00:00。这是已落盘视频的阶段快照；评分更新至 2026-10-29T18:48:47.070663+00:00，后续实验仍在原运行目录继续。

- 首批正式评价：**22/32** 条完整评分，0 条评价异常；包括直接提示词预实验、历史单次 Planner 和原片对照。
- [视频与逐项评分页面](first_wave/review.html)：克隆仓库后在浏览器打开；GitHub 可下载 HTML。
- [逐视频记录](first_wave/records.json) · [分项汇总](first_wave/report/report.md) · [CSV](first_wave/report/metrics.csv) · [待评价清单](first_wave/status.json)。
- [冻结任务卡](first_wave/cards)与[原始评价 manifest](first_wave/manifest.original.json)保留原版本；导出 manifest 只调整资源位置。

## 生成视频

| 类别 | 已完成视频 | 含义 |
|---|---:|---|
| 直接提示词预实验 | 20 | 生成完成，评价状态见对应批次 |
| 历史 Planner 单次编辑 | 8 | 生成完成，评价状态见对应批次 |
| 旧版固定路线 loop 追加轮次 | 22 | 生成完成，评价状态见对应批次 |
| 知识库可用性消融 | 4 | 生成完成，评价状态见对应批次 |

## 视频、提示词与执行记录

| 类别 / 模型 / 条件 | 视频 | 实际输入与提示词 | 执行结果 |
|---|---|---|---|
| 直接提示词预实验 / bernini / 024__long | [播放或下载](media/3a085bd7dc580c3c8fe67e0071c056e582f88001e0a81ce2368e19d4256f2cd1.mp4) | [input.json](cases/prompt_preexperiment__bernini__024__long/input.json) | [result.json](cases/prompt_preexperiment__bernini__024__long/result.json) |
| 直接提示词预实验 / bernini / 024__long_keep | [播放或下载](media/b3b8b4cc6e829021e19d1126309a9fe23e62646eab3f624b2173771cfbb1a796.mp4) | [input.json](cases/prompt_preexperiment__bernini__024__long_keep/input.json) | [result.json](cases/prompt_preexperiment__bernini__024__long_keep/result.json) |
| 直接提示词预实验 / bernini / 027__long | [播放或下载](media/1ec406b5563568822f8d06851abb81537b8113f6046ff44a07b35b1c0f3ce16f.mp4) | [input.json](cases/prompt_preexperiment__bernini__027__long/input.json) | [result.json](cases/prompt_preexperiment__bernini__027__long/result.json) |
| 直接提示词预实验 / bernini / 027__long_keep | [播放或下载](media/5f624085e062729e9b35f9326be306dff7e87b1beea3c49857bc1600a30b49a5.mp4) | [input.json](cases/prompt_preexperiment__bernini__027__long_keep/input.json) | [result.json](cases/prompt_preexperiment__bernini__027__long_keep/result.json) |
| 直接提示词预实验 / bernini / 027__short | [播放或下载](media/1269d52ce2626bf0cad6bfc5430595fe367e9c024082da7e6a7efec31a9f60c1.mp4) | [input.json](cases/prompt_preexperiment__bernini__027__short/input.json) | [result.json](cases/prompt_preexperiment__bernini__027__short/result.json) |
| 直接提示词预实验 / bernini / 041__long | [播放或下载](media/d8875e3d451a060367de30cab9057d9329506b585a1bb1439802ce828ae18f8d.mp4) | [input.json](cases/prompt_preexperiment__bernini__041__long/input.json) | [result.json](cases/prompt_preexperiment__bernini__041__long/result.json) |
| 直接提示词预实验 / bernini / 041__long_keep | [播放或下载](media/49c26315f1b1bab5ae4b9a1f909bbe4490717934c8c0156e92a4c112a8f1001c.mp4) | [input.json](cases/prompt_preexperiment__bernini__041__long_keep/input.json) | [result.json](cases/prompt_preexperiment__bernini__041__long_keep/result.json) |
| 直接提示词预实验 / bernini / 041__short | [播放或下载](media/6a9961b509bfa8c5b312fa5cbb7a4b09e05ba107f7bde9a7e764bccbcb2fa2a4.mp4) | [input.json](cases/prompt_preexperiment__bernini__041__short/input.json) | [result.json](cases/prompt_preexperiment__bernini__041__short/result.json) |
| 直接提示词预实验 / bernini / fewshot_004__long | [播放或下载](media/4dcdac10fbb987091ecb89d05a2d913f5102d46fb6feb48b3193504931fd551c.mp4) | [input.json](cases/prompt_preexperiment__bernini__fewshot_004__long/input.json) | [result.json](cases/prompt_preexperiment__bernini__fewshot_004__long/result.json) |
| 直接提示词预实验 / bernini / fewshot_004__long_keep | [播放或下载](media/f8f6ccb0eba548a6a4890636f04a03986e6fe6e7519ec3f57f6b6728a7aac3b0.mp4) | [input.json](cases/prompt_preexperiment__bernini__fewshot_004__long_keep/input.json) | [result.json](cases/prompt_preexperiment__bernini__fewshot_004__long_keep/result.json) |
| 直接提示词预实验 / ditto / 024__long | [播放或下载](media/4fe84c16a08a9bdae8613eec3260d112d001cca6a5367ea8740f8ba5d5ec6f0a.mp4) | [input.json](cases/prompt_preexperiment__ditto__024__long/input.json) | [result.json](cases/prompt_preexperiment__ditto__024__long/result.json) |
| 直接提示词预实验 / ditto / 024__long_keep | [播放或下载](media/62316dea35336318a92fcdd2ead8531fbe0279ba2abc54fad0200130367b6744.mp4) | [input.json](cases/prompt_preexperiment__ditto__024__long_keep/input.json) | [result.json](cases/prompt_preexperiment__ditto__024__long_keep/result.json) |
| 直接提示词预实验 / ditto / 027__long | [播放或下载](media/a575b96319fad2d805e3498cb5a5c157a9616129d04352d0927caa612124ed3b.mp4) | [input.json](cases/prompt_preexperiment__ditto__027__long/input.json) | [result.json](cases/prompt_preexperiment__ditto__027__long/result.json) |
| 直接提示词预实验 / ditto / 027__long_keep | [播放或下载](media/aec694ef36c414966f716a7e184899d17a59d3ecb1c22cfb369b15bfde796b53.mp4) | [input.json](cases/prompt_preexperiment__ditto__027__long_keep/input.json) | [result.json](cases/prompt_preexperiment__ditto__027__long_keep/result.json) |
| 直接提示词预实验 / ditto / 027__short | [播放或下载](media/11b7c7240e3527d418455f25984b1aefdb2fef3c83c5b85897f84a436a571944.mp4) | [input.json](cases/prompt_preexperiment__ditto__027__short/input.json) | [result.json](cases/prompt_preexperiment__ditto__027__short/result.json) |
| 直接提示词预实验 / ditto / 041__long | [播放或下载](media/59df455539cc6ea9d7b6988cf1e663676fcd1c7ac6758527a02a4f72632e2889.mp4) | [input.json](cases/prompt_preexperiment__ditto__041__long/input.json) | [result.json](cases/prompt_preexperiment__ditto__041__long/result.json) |
| 直接提示词预实验 / ditto / 041__long_keep | [播放或下载](media/0482749fc23f83d803b985dac23cb68d8579f0ce9750bacdf5e346145655c2b8.mp4) | [input.json](cases/prompt_preexperiment__ditto__041__long_keep/input.json) | [result.json](cases/prompt_preexperiment__ditto__041__long_keep/result.json) |
| 直接提示词预实验 / ditto / 041__short | [播放或下载](media/4b96c51685f8a3d038614167c15b5dd6e159c1731e1978fdb2e9c8ee6c327e0d.mp4) | [input.json](cases/prompt_preexperiment__ditto__041__short/input.json) | [result.json](cases/prompt_preexperiment__ditto__041__short/result.json) |
| 直接提示词预实验 / ditto / fewshot_004__long | [播放或下载](media/8d8be1abd228e2f44f0c9ac6b0b2e7f79bd7844f42ff4292c751d53eb45d779c.mp4) | [input.json](cases/prompt_preexperiment__ditto__fewshot_004__long/input.json) | [result.json](cases/prompt_preexperiment__ditto__fewshot_004__long/result.json) |
| 直接提示词预实验 / ditto / fewshot_004__long_keep | [播放或下载](media/6cc19bd6dedf957f50ea61f12dadb34b938abb3c8357ad2afdc17113f5ab84b3.mp4) | [input.json](cases/prompt_preexperiment__ditto__fewshot_004__long_keep/input.json) | [result.json](cases/prompt_preexperiment__ditto__fewshot_004__long_keep/result.json) |
| 历史 Planner 单次编辑 / bernini / 024__planner | [播放或下载](media/025008264d78e21bdb4bb8518659ffaf3271daf7ad59020b13beb9e8f9f726bc.mp4) | [input.json](cases/planner_single_edit__bernini__024__planner/input.json) | [result.json](cases/planner_single_edit__bernini__024__planner/result.json) |
| 历史 Planner 单次编辑 / bernini / 027__planner | [播放或下载](media/c9dd33efcfd591846e18d1bf478cf159bdb94ac54af0c9ad9cb9520dcc8dcb58.mp4) | [input.json](cases/planner_single_edit__bernini__027__planner/input.json) | [result.json](cases/planner_single_edit__bernini__027__planner/result.json) |
| 历史 Planner 单次编辑 / bernini / 041__planner | [播放或下载](media/084845954240b71d1ab83f376215da0eeaf6b57b08e1ca13be35ee8dac4a4c4f.mp4) | [input.json](cases/planner_single_edit__bernini__041__planner/input.json) | [result.json](cases/planner_single_edit__bernini__041__planner/result.json) |
| 历史 Planner 单次编辑 / bernini / fewshot_004__planner | [播放或下载](media/7fcc2cca80405e35344700779265ea9e7f8bb79cd24923383396e1c29fc4762f.mp4) | [input.json](cases/planner_single_edit__bernini__fewshot_004__planner/input.json) | [result.json](cases/planner_single_edit__bernini__fewshot_004__planner/result.json) |
| 历史 Planner 单次编辑 / ditto / 024__planner | [播放或下载](media/c19851e110af7f7bb328f0adc053ed2883724e74df79b6ed4ab35da36acc8bc2.mp4) | [input.json](cases/planner_single_edit__ditto__024__planner/input.json) | [result.json](cases/planner_single_edit__ditto__024__planner/result.json) |
| 历史 Planner 单次编辑 / ditto / 027__planner | [播放或下载](media/e69d8eeccd3e468c7c716ff0f81b93b07eefc0920a08a40b0c2e153558d13d4e.mp4) | [input.json](cases/planner_single_edit__ditto__027__planner/input.json) | [result.json](cases/planner_single_edit__ditto__027__planner/result.json) |
| 历史 Planner 单次编辑 / ditto / 041__planner | [播放或下载](media/6701a4f8ac8ccc818b834d537b0056bd9b66d3bcc1d1a98847cba01e93e35b0f.mp4) | [input.json](cases/planner_single_edit__ditto__041__planner/input.json) | [result.json](cases/planner_single_edit__ditto__041__planner/result.json) |
| 历史 Planner 单次编辑 / ditto / fewshot_004__planner | [播放或下载](media/fa2d443e25f190ace4676bf28a81e6727596d843bfd07914a7d57d7a3e216690.mp4) | [input.json](cases/planner_single_edit__ditto__fewshot_004__planner/input.json) | [result.json](cases/planner_single_edit__ditto__fewshot_004__planner/result.json) |
| 旧版固定路线 loop 追加轮次 / bernini / 041__cumulative__r2 | [播放或下载](media/775879d45f8653d95eae9cd0ce0d2852eef434f7ac0ba8e8d50eaeab874631b9.mp4) | [input.json](cases/legacy_route_loop__bernini__041__cumulative__r2/input.json) | [result.json](cases/legacy_route_loop__bernini__041__cumulative__r2/result.json) |
| 旧版固定路线 loop 追加轮次 / bernini / 041__cumulative__r3 | [播放或下载](media/e90c9b7b2fbef98d463657332c3f40477e54b84acfbb2cbab8d0fc104f62ad9c.mp4) | [input.json](cases/legacy_route_loop__bernini__041__cumulative__r3/input.json) | [result.json](cases/legacy_route_loop__bernini__041__cumulative__r3/result.json) |
| 旧版固定路线 loop 追加轮次 / bernini / 041__fixed__r2 | [播放或下载](media/f10fc01632fa4c7a238e95218b7492aec90185c6d810b9bdfd286652f5edb1af.mp4) | [input.json](cases/legacy_route_loop__bernini__041__fixed__r2/input.json) | [result.json](cases/legacy_route_loop__bernini__041__fixed__r2/result.json) |
| 旧版固定路线 loop 追加轮次 / bernini / 041__fixed__r3 | [播放或下载](media/6ee192c06cace5f2485df4e9c9d544792d5d9ba1c83fbc6dec2ebcaf5e3fdb12.mp4) | [input.json](cases/legacy_route_loop__bernini__041__fixed__r3/input.json) | [result.json](cases/legacy_route_loop__bernini__041__fixed__r3/result.json) |
| 旧版固定路线 loop 追加轮次 / bernini / 041__incremental__r2 | [播放或下载](media/acb1ceaf6123c3ccbf50cc87e72eb16c4f199a6d808b23112c8af6bbf8db872f.mp4) | [input.json](cases/legacy_route_loop__bernini__041__incremental__r2/input.json) | [result.json](cases/legacy_route_loop__bernini__041__incremental__r2/result.json) |
| 旧版固定路线 loop 追加轮次 / bernini / 041__incremental__r3 | [播放或下载](media/c8379f18dea007a7fc685b33189eb4c62854166b9a9bcf95570b4523a2d338df.mp4) | [input.json](cases/legacy_route_loop__bernini__041__incremental__r3/input.json) | [result.json](cases/legacy_route_loop__bernini__041__incremental__r3/result.json) |
| 旧版固定路线 loop 追加轮次 / bernini / 041__restart__r2 | [播放或下载](media/7d310b2e426072c187f08590206b2068a79bb3d92e3cfcbe6e76e63a16a89ee9.mp4) | [input.json](cases/legacy_route_loop__bernini__041__restart__r2/input.json) | [result.json](cases/legacy_route_loop__bernini__041__restart__r2/result.json) |
| 旧版固定路线 loop 追加轮次 / bernini / 041__restart__r3 | [播放或下载](media/9cccb24d3ddb74ec0355f7b063bfb0f930515d2fbd542babda56323c683e59fd.mp4) | [input.json](cases/legacy_route_loop__bernini__041__restart__r3/input.json) | [result.json](cases/legacy_route_loop__bernini__041__restart__r3/result.json) |
| 旧版固定路线 loop 追加轮次 / bernini / fewshot_004__cumulative__r2 | [播放或下载](media/4ae2e56034bef3d9458cd8b5f775819ffd8f5f7f1ea5feba9329e272d55335ad.mp4) | [input.json](cases/legacy_route_loop__bernini__fewshot_004__cumulative__r2/input.json) | [result.json](cases/legacy_route_loop__bernini__fewshot_004__cumulative__r2/result.json) |
| 旧版固定路线 loop 追加轮次 / bernini / fewshot_004__cumulative__r3 | [播放或下载](media/ec04adc901d7161696fca42b27cb96262fa3951ebff8f5011d2a6d00aee35665.mp4) | [input.json](cases/legacy_route_loop__bernini__fewshot_004__cumulative__r3/input.json) | [result.json](cases/legacy_route_loop__bernini__fewshot_004__cumulative__r3/result.json) |
| 旧版固定路线 loop 追加轮次 / bernini / fewshot_004__fixed__r2 | [播放或下载](media/0cbebeab657b7373ab2d1816658e8709f8e3a591d580a1c027b1c136c98fc776.mp4) | [input.json](cases/legacy_route_loop__bernini__fewshot_004__fixed__r2/input.json) | [result.json](cases/legacy_route_loop__bernini__fewshot_004__fixed__r2/result.json) |
| 旧版固定路线 loop 追加轮次 / bernini / fewshot_004__fixed__r3 | [播放或下载](media/86c5675fe66391acacd1dc670b2bc28613f1ac76470960e138680da57aeebbb9.mp4) | [input.json](cases/legacy_route_loop__bernini__fewshot_004__fixed__r3/input.json) | [result.json](cases/legacy_route_loop__bernini__fewshot_004__fixed__r3/result.json) |
| 旧版固定路线 loop 追加轮次 / bernini / fewshot_004__incremental__r2 | [播放或下载](media/8f6dc3a3b82788d668b694816a2674912b78f9be12d7f87d98995bfe35a3ec21.mp4) | [input.json](cases/legacy_route_loop__bernini__fewshot_004__incremental__r2/input.json) | [result.json](cases/legacy_route_loop__bernini__fewshot_004__incremental__r2/result.json) |
| 旧版固定路线 loop 追加轮次 / bernini / fewshot_004__incremental__r3 | [播放或下载](media/e9091b9bf2741c4092e71b774d374f9132ad13e64b7f2b83132880ffc0e949cb.mp4) | [input.json](cases/legacy_route_loop__bernini__fewshot_004__incremental__r3/input.json) | [result.json](cases/legacy_route_loop__bernini__fewshot_004__incremental__r3/result.json) |
| 旧版固定路线 loop 追加轮次 / bernini / fewshot_004__restart__r2 | [播放或下载](media/7d7ae60aa6949f0f455f4fae3bd8a0719dfabceeb3bef672f54919a95e4ba3cc.mp4) | [input.json](cases/legacy_route_loop__bernini__fewshot_004__restart__r2/input.json) | [result.json](cases/legacy_route_loop__bernini__fewshot_004__restart__r2/result.json) |
| 旧版固定路线 loop 追加轮次 / bernini / fewshot_004__restart__r3 | [播放或下载](media/c29b4db396878ed5dbf3f3bc8991a8b9e15f425070058b59dfc09845e332fc81.mp4) | [input.json](cases/legacy_route_loop__bernini__fewshot_004__restart__r3/input.json) | [result.json](cases/legacy_route_loop__bernini__fewshot_004__restart__r3/result.json) |
| 旧版固定路线 loop 追加轮次 / ditto / 041__cumulative__r2 | [播放或下载](media/35a5bef020fc08e63a7fb7e4a91aa66e741154859e59cf3f63985c4e8ecc43b3.mp4) | [input.json](cases/legacy_route_loop__ditto__041__cumulative__r2/input.json) | [result.json](cases/legacy_route_loop__ditto__041__cumulative__r2/result.json) |
| 旧版固定路线 loop 追加轮次 / ditto / 041__fixed__r2 | [播放或下载](media/d59f6fe8424bc447efb6c4c525153808a7806e463f6829e4826a766fc15efdb2.mp4) | [input.json](cases/legacy_route_loop__ditto__041__fixed__r2/input.json) | [result.json](cases/legacy_route_loop__ditto__041__fixed__r2/result.json) |
| 旧版固定路线 loop 追加轮次 / ditto / 041__fixed__r3 | [播放或下载](media/be811a71269cc3b50dbcebb988c46c7db3fa9137803a029607a7a15342109d84.mp4) | [input.json](cases/legacy_route_loop__ditto__041__fixed__r3/input.json) | [result.json](cases/legacy_route_loop__ditto__041__fixed__r3/result.json) |
| 旧版固定路线 loop 追加轮次 / ditto / 041__incremental__r2 | [播放或下载](media/f4b6ceafe16651ae24c6af693b94076bffb8b7ecc008096145e8ace7faf348d0.mp4) | [input.json](cases/legacy_route_loop__ditto__041__incremental__r2/input.json) | [result.json](cases/legacy_route_loop__ditto__041__incremental__r2/result.json) |
| 旧版固定路线 loop 追加轮次 / ditto / fewshot_004__fixed__r2 | [播放或下载](media/8b03858b22cf0bd03231592348d9960c80bda6836d461a2ebf61d7d06d623b4b.mp4) | [input.json](cases/legacy_route_loop__ditto__fewshot_004__fixed__r2/input.json) | [result.json](cases/legacy_route_loop__ditto__fewshot_004__fixed__r2/result.json) |
| 旧版固定路线 loop 追加轮次 / ditto / fewshot_004__fixed__r3 | [播放或下载](media/5b6fff816b51fcd3533ea4461dd5d8e0a34f278d0559c005e359dc51ec7d76e2.mp4) | [input.json](cases/legacy_route_loop__ditto__fewshot_004__fixed__r3/input.json) | [result.json](cases/legacy_route_loop__ditto__fewshot_004__fixed__r3/result.json) |
| 知识库可用性消融 / bernini / 041__short__full_knowledge | [播放或下载](media/d01a7e3844387978f49e00ad436bc22b1a439fa363c6cc60d1fc4f0ef334de8b.mp4) | [input.json](cases/knowledge_ablation__bernini__041__short__full_knowledge/input.json) | [result.json](cases/knowledge_ablation__bernini__041__short__full_knowledge/result.json) |
| 知识库可用性消融 / bernini / 041__short__no_knowledge | [播放或下载](media/c0bba88d0ebff33f1ba88df2c69a90ac6f397a20235ab067e31760aca0aef9f1.mp4) | [input.json](cases/knowledge_ablation__bernini__041__short__no_knowledge/input.json) | [result.json](cases/knowledge_ablation__bernini__041__short__no_knowledge/result.json) |
| 知识库可用性消融 / ditto / 041__short__full_knowledge | [播放或下载](media/e2268e1bbc70c10a3c477374ae2088aa617417c285500d8e77ac6da7d718e754.mp4) | [input.json](cases/knowledge_ablation__ditto__041__short__full_knowledge/input.json) | [result.json](cases/knowledge_ablation__ditto__041__short__full_knowledge/result.json) |
| 知识库可用性消融 / ditto / 041__short__no_knowledge | [播放或下载](media/cb37cadb08befe65747255eff33a972590f86d2a1750703419df6b5e5ae78a5c.mp4) | [input.json](cases/knowledge_ablation__ditto__041__short__no_knowledge/input.json) | [result.json](cases/knowledge_ablation__ditto__041__short__no_knowledge/result.json) |

## 版本与使用说明

- [消融实际知识暴露记录](ablation/knowledge-use-audit.md)：两臂共享冻结版本，full 的手册注入与知识可用性共同变化；主动检索次数以记录为准。
- [消融冻结代码与知识](ablation/frozen-experiment.zip)与[逐文件哈希](ablation/freeze.json)保留实验实际版本。
- 新 Critic 已产出的完整反馈：041；见 [验证目录](critic_v2)。该演示止于 Planner 下一步请求，尚未生成新视频。
- 预实验、旧路线 loop、新版 Planner/Critic 与正式盲评分别记录；本快照不合并为一种方法成绩。
- CLIP-F、DINO-F 尚未实测。原生连续帧图像缓存保留在本地，快照含证据索引、原视频和生成视频。
- `videos.json` 记录每份视频的原位置、SHA-256 和字节数；重复视频按哈希共享文件。
- [机器可读快照状态](snapshot.json)。

## 提交前检查

8 组本地检查通过，覆盖 Planner、Critic、生成任务接入、经验更新、旧 loop 与独立评价；详见 [检查记录](validation.json)。视频哈希与报告链接检查见 [资源核验](artifact-checks.json)。旧版修订接口的 source/original 标记兼容问题已修复。

代码对应提交 `e77ef87916a9c75a299e7e7253e0eaeaebc592da`。消融视频数量按已校验文件计算，见 [导出状态](ablation/snapshot-status.json)；保留的调度状态是更早的检查点。
