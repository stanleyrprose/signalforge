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
