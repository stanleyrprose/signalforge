# S52 / S53 source actual listing and PDF acceptance — 2026-10-16

New source identity: S52 = Kyemon (ကြေးမုံ), S53 = Myanma Alinn (မြန်မာ့အလင်း).

**Real Bangkok / Mac joint read-only verification**

- MOI official index: both HTTP 200 and parsed **7 edition download entries**. Latest URLs:
  - S52 `https://www.moi.gov.mm/km/file-download/download/public/5395`
  - S53 `https://www.moi.gov.mm/mal/file-download/download/public/5762`
- 2026-10-16 original PDF pages: 32 per paper; PDF bytes: 3,602,175 (S52), 2,787,343 (S53).
- Native PDF extraction includes nonstandard Burmese PUA code points. The fail-closed parser produces **0 verified formal tenders** for each actual daily PDF, so no business Signal is fabricated from corrupt text.
- Developer-branch registry counts **30** enabled source definitions; Bangkok **production still has 28**. Newly added S52/S53 are **not deployed or activated**.
- Focused source parser tests: 4/4 pass. Full SignalForge tests after source-ID contract correction and bounded manual-review TG sender tests: **500/500 pass**.
- Manual-review samples have been delivered by the production-configured SignalForge Bot from Bangkok, **not** the tender delivery pipeline: R01 messages 377/378 (Kyemon p28 source + Chinese machine sample), R02 messages 379/380 (Myanma Alinn p28 source + Chinese machine sample). These sample translations are not proof of successful all-page OCR/translation.
- Real Mac optical OCR: first 1,100 characters of page 28 were translated for each. Confidence is about 65% / 69% and multi-column ordering has not yet been manually accepted. Source-specific originals and sample checkpoints are kept outside Git in a private Mac QA directory.

## 2026-10-16 产品变更与重新人工验收（最新）

用户明确放弃两报“整期逐字翻译和照搬版面”的要求；当前 Mac 目标是**仅保留新闻、删除广告和无关信息、按新闻主题编排**。SignalForge 的 S52/S53 *招标来源*仍与 Mac 新闻编辑版完全分离。

- R01/R02 的第28页广告试译 **已作废**，不得作为新要求的验收结果。
- 实际处理《镜报》和《缅甸之光》各自当天**第1、2页**；全报每份32页。Mac PDFKit/Tesseract OCR 后，经现有 Codex OAuth 提取新闻并过滤广告/非新闻条目，各报模型初筛过滤计数为 9（非人工核准总数）。
- 《镜报》保留 2 条报道：基层义诊、佛学考试；《缅甸之光》保留一篇粮食安全的社论。混合字体地名已改为 `[原文地名待核]`，不伪造精确地名。
- 中文编辑版以新闻类别组织，不复刻原报版面；生成各 1 页的中文版 PDF 并附原报前2页 PDF 比对。
- **Bangkok VPS 使用既有 SignalForge TG Bot 新发起验收**：R03 原文381 / 中文新闻 PDF 382 / 说明383；R04 原文384 / 中文新闻PDF385 / 说明386。生产TG没有发送为tender Signal，独立回执保存在 VPS 私有 SignalForge state。
- 两项审核状态均为 `PENDING_USER_REVIEW`，未收到通过结果时不执行整期新闻自动编辑/日报。
- 目前 S52/S53 仍未进入 SignalForge main/生产，新源代码仍是开发分支；与新闻编辑版样稿发送无关。

## Release gate

Do not call source GREEN or tender coverage complete on an empty parser result. Await R01/R02 human feedback before attempting full-edition daily publication. Correct publication workflow requires separate PR/CI/merge and Bangkok release authorization. Keep the Mac entire-paper translation pipeline independent of SignalForge S52/S53 tender-source identity.


## 2026-10-16 R04 FAIL，R05 已重新发送

用户反馈《缅甸之光》R04漏报严重，Mac补做当期32页完整OCR和候选审计（121个页内候选、116个去重候选）。修复前2页偏差和LOW静默丢失，并恢复NCA、价格数据、政策、工程与能源招标信息。R05材料经Bangkok SignalForge Bot发送：官方PDF message 387、重点中文新闻QA 388、覆盖审计389、说明390。Telegram只用于**人工审核**，不触发正式Tender Signal。R05正在等待人工回复；SignalForge S52/S53两新来源尚未部署，生产仍28源。

## 2026-10-16 R05 FAIL → R06 完整新闻对账

用户再次判定 R05 FAIL：Coverage Audit 已有121条候选、116条初步去重，但 Key News 硬编码挑选20条导致内容遗漏。Mac News Publisher 增加逐条对账：最终R06共121条候选，115条独立新闻，5条NCA/G20同一事件关联报道以正文续文形式保留合并，1条残缺待核。所有候选附文章ID、原报页码、明确去向。82篇仍需内容/专名核实；这不是最终正式审定新闻。

由Bangkok VPS上 **SignalForge现有Bot** 发送新审核稿，消息ID 391（28页完整版中文新闻PDF）、392（4页逐条去向Audit）、393（验收说明）。Telegram发送未写入SignalForge business signals，回执已存入Bangkok private state。生产依旧原有28源，没有将新报纸源部署到生产；无自动日报。

## 2026-10-16 R06 PASS — 手机阅读Digest新增（独立新闻流程）

用户R06完整中文新闻PDF版式/覆盖率审核通过。明确要求：以后每次由Bangkok推送两份报纸中文新闻PDF时，**同时推送一条从全文提炼的高价值中文Digest**（不是R05的Top20删减版）。Digest通常8–12条，以Myanmar政策/NCA、电信、工程能源国企招标、投资、燃油、外汇等优先；逐条保留正文Nnnn编号、原报页码、简明说明和风险提示。不会向传统Tender Signal写入内容。

Mac `macmini_automation`新增 `scripts/newspaper_digest.py`：复用完整版新闻清单，确定性选择12条，按Telegram 4096 UTF-16长度拆分，JSON同时绑定官方PDF SHA及中文版PDF SHA，不额外调用LLM。

本仓库新增 `tools/send_newspaper_daily_digest_tg.py`：Bangkok原有SignalForge Bot发送顺序为 **Digest消息→完整版中文版PDF**，按paper/date/SHA保留持久回执，失败不可盲目重发。对于R06已发送过的PDF（旧消息391），通过`--digest-only --preview`仅发了Digest试运行，Telegram实际消息 **394**。不同于S52/S53招标source采集，完整新闻翻译+摘要的代码继续由Mac仓库管理。

当前仅为开发分支/实测投递；未PR/CI/Merge，未开启定时自动日报，也未部署S52/S53新source。正式启用须获得分阶段授权，并先验证新闻Digest稿可读性。

## Digest Rev2 — 增加AI语义新闻编辑校验

用户再次调整新闻优先级：政治/政策、经济、地缘政治、国际关系、民生社会、国内冲突/和平进程优先，工程招标只保留重大影响；AI需评估事件的新信息量并引用已有旧期新闻。Mac开发`newspaper_digest_ai.py`且要求全部文章都得到AI评估，Bangkok的`send_newspaper_daily_digest_tg.py`现在能验收严格的`newspaper-digest-v2`协议。真实调用Codex OAuth遭遇额度限制，**尚未产生或推送AI真实Digest**；旧TG 394仍是规则版。投递流程仍处开发分支，正式生产不变。详细见`docs/NEWSPAPER-DIGEST-V2-CONTRACT.md`。
