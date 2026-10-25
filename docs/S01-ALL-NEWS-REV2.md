# S01 全量中文资讯 Rev2 — 实施规格

状态：已批准实施规格。2026-10-25 的[用户修订](NEWS-PROCESSING-POLICY-20261025.md)优先适用：投递成功后清理全部任务内容文件，仅留最小防重与回执；正文、AI结果及逐日处理数据库仅在处理/恢复期间保留。当前正文格式为 Markdown；已部署及真实投递事实见[运维证据](CURRENT-OPERATIONS.md)。
日期：2026-10-17
上位依据：[三路新闻交付契约](S01-S52-S53-NEWS-DELIVERY-CONTRACT.md)；本文件更新 S01 非招投标新闻输出范围，不改变 Tender Core。

## 产品目标

每天抓取 S01 Myanmar National Portal 的新闻列表（多页）和文章正文，对所有可识别的独立新闻进行中文翻译、摘要与排序，向 Bangkok 的现有 SignalForge Telegram Bot 发送一条简短 Digest 和一份完整中文 Markdown。**重要性只决定排序，绝不决定是否收录。** 广告、页面导航和非新闻组件不是新闻；相同新闻可去重。失败、缺失和待补发记录不得静默消失。

## 隔离边界

新闻专用 SQLite、新闻证据、新闻发送回执；不写入 Tender Core 的 canonical TENDER、signals、tender delivery receipts 或 Source Registry。Mac 负责来源获取、AI 中文处理与 Markdown 生成；Bangkok 独立发送 Telegram。保持 Tender Core 的日调度不变。

## 一次日报的状态流

1. 每天按既定时间启动一次。读取 S01 多页列表，保留每页的抓取结果、失败原因、列表 SHA、原始 URL 和候选数量。页数可配置且有上限，不能把固定 84 条当成每日配额。
2. 对文章使用规范化 issuer/article identity 去重；只对新增或正文实质变化的文章提取、翻译，保留原始正文、SHA 与 AI 结果。标题或 URL 变化本身不能触发重复发送；身份不确定的合并须标记待审核，不得误删。
3. AI 输出完整中文标题、详细摘要、重要性、类别、依据、证据限制。每篇已处理文章都进入 Markdown。无正文或翻译失败者进入待补发队列，日报清楚列出未完成数，不把它们计为成功翻译。
4. 发送 Digest（按政治/政策、经济、外交、地缘、民生、冲突等优先排序）及覆盖所有已处理新闻的中文 Markdown。Digest 可短，正文不可按分数裁剪。
5. 每次发送先创建稳定的 `edition_id`（来源+日期+正文版本），并持久化独立的发送状态；Telegram 返回 message_id 后才写 SUCCESS。网络超时写 UNKNOWN，**不得盲目重试**；先对账，确认未送达才补发。
6. 对同一篇文章，同一天或跨天已成功发送且内容未实质变化时，不重复发送。日报即使无新增也可发一条“无新增”状态消息，不能重复附送旧正文。
7. 输出覆盖审计：列表页数、列表候选、去重数、唯一文章数、正文成功/失败、AI 成功/失败、正文包含数、Telegram SUCCESS/UNKNOWN/FAILED、待补发数。数目必须对得上。

## 质量与验收

- 内容基准：2026-10-16 审核批次 84 条、24 页中文 PDF，Telegram message_id 401；不把这次的人工发送当成日调度验收。
- 重点验证：真实列表分页、跨页重叠、跨日增量、同文章不同 URL、正文更新、AI 缺失、Markdown 完整性、发送超时 UNKNOWN、重试去重、消息 ID 回执。
- 所有新闻必须有原始 URL；数字、日期、主体不可推断。S01 来源的 TLS 验证例外必须保留证据风险标记。
- 部署前必须通过单独审核：代码审查 → 获授权后测试 → PR/CI/Merge 授权 → Bangkok 部署授权 → 连续日验收。
- 不再适用 Rev1 的“过滤体育/例行会议/普通新闻”作为全量新闻输出的规则。Rev1 的高价值情报分类可继续作为排序标签，不再作为收录门槛。

## Daily Runner（当前代码接口）

`python3 -m signalforge.s01_daily_runner --root <S01Daily根目录> --date <YYYY-MM-DD>` 默认只生成审核稿，不发送 Telegram。加入 `--publish` 才会执行 Bangkok 传输。入口持有单进程锁，先核对分页、正文和 AI 覆盖，再生成 Markdown 和发送；失败时不跳过审计。当前 runner 使用 Mac Codex CLI OAuth 和到 Bangkok 的 SSH 配置；默认 Markdown 路径不需要 PyMuPDF 或中文字体。历史 PDF 预览路径仍可保留。当前目标为每日自动调度；是否已启用、实际采集与TG投递是否成功，必须检查Mac/Bangkok运行日志和Telegram回执，不得从本文件推断。

**历史风险及当前静态事实：** 初版 review runner 曾有历史文章混入风险；当前 daily runner 为每个日期使用 `evidence/<day>/s01-news-review.sqlite`，并通过持久化投递 ledger 管理跨日去重。跨日去重和当前投递事实按日期记录在运维证据中；新改动仍须独立验证。不要把代码部署等同于已启用每日自动日报。
