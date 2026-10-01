# Tender Radar External Pilot Launch Playbook

## Objective

Validate whether Chinese suppliers, Myanmar distributors, EPCs, system integrators, telecom/ICT vendors, and power/engineering suppliers will pay for a high-signal Myanmar government/SOE Tender feed.

Do not build self-service SaaS before this test.

## Offer

Customer-facing promise:

> We monitor Myanmar government and SOE procurement sources every day and send only tenders relevant to your products to Telegram in Chinese, including buyer, procurement scope, quantity/scale when disclosed, deadline, participation information, and the official source.

Pilot pricing hypothesis:

- RMB 200–500/month for an individual company pilot;
- one-month manual onboarding;
- no setup fee during validation;
- no long-term contract.

Pricing is a hypothesis, not a validated market price.

## Qualification

Prefer companies where all are true:

1. already sell equipment/services into Myanmar or are actively entering;
2. government/SOE procurement can materially affect revenue;
3. current Tender discovery depends on people checking websites, Facebook, groups, email, partners, or forwarding screenshots;
4. missing one relevant Tender has real economic cost;
5. a decision-maker or sales owner can give direct weekly feedback.

Avoid early pilots that only want generic Myanmar news.

## Manual onboarding

For each customer capture:

- company name;
- profile_id;
- industries/relevance categories;
- 10–30 concrete product/service keywords;
- target buyers;
- explicit exclusion terms;
- Telegram chat ID;
- one commercial owner;
- one feedback owner.

Create one reviewed Business Profile JSON. Start with deterministic matching; do not use LLM-only relevance decisions.

Run a dry preview first:

```sh
signalforge telegram-deliver \
  --dry-run \
  --translate-preview \
  --profile /path/to/customer.json
```

Review false positives before enabling delivery.

## Weekly pilot metrics

For each profile track:

- Tenders delivered
- Relevant
- Not relevant
- Clicked / acknowledged
- Took Action
- Bid / Quote Initiated
- explicit Would Pay / Would Not Pay
- false positives by keyword/category/buyer
- missed Tender reported by customer

Do not use source count as the primary success metric.

## Go / adjust / stop

Suggested validation gate after 10 target companies:

- GO: >=3 companies explicitly willing to pay RMB 200–500/month or equivalent;
- ADJUST: strong relevance/use but weak willingness to pay -> revisit ICP, packaging, urgency, or price;
- STOP/REPOSITION: zero willingness to pay and low customer action despite adequate Tender relevance.

Do not solve weak demand by adding dashboard features.

## Productization only after evidence

If the pilot shows payment and action:

1. multi-profile delivery operations hardening;
2. profile onboarding API or lightweight admin UI;
3. per-customer Telegram routing;
4. customer feedback analytics;
5. subscription/billing;
6. Cloudflare Worker + D1 control plane if operations justify it.

Keep heavy crawling, browser execution, OCR, and document processing on SignalForge/Bangkok/Mac rather than forcing them into Workers.

## First outreach message

Chinese:

> 我们正在测试一项面向在缅甸做政府/国企业务供应商的招投标情报服务。系统每天自动扫描缅甸政府和国企的采购公告，只把与你公司产品相关的项目筛出来，并用中文发送到 Telegram，包含采购方、采购内容、数量/规模、截止时间以及官方原文。现在开放少量试用名额，想找真正做缅甸项目的公司测试一个月。核心不是“多发新闻”，而是尽量减少漏标和无关信息。如果你愿意，我可以先按你们的产品范围做一份免费样例。

## Interview questions

During onboarding ask:

1. 你们目前从哪里获取缅甸政府/国企招标信息？
2. 谁负责每天看这些信息？
3. 最近一年有没有因为发现太晚、语言、信息分散而错过项目？
4. 哪些采购方对你最重要？
5. 你真正希望看到的是哪些产品/工程类型？
6. 哪些信息一出现你就会立刻行动？
7. 如果每天只收到与你业务高度相关的 Tender，你希望通过什么渠道收到？
8. 如果这项服务稳定帮助你减少漏标，你愿意每月支付多少？
9. 什么情况下你会取消订阅？

Record answers as evidence; do not reinterpret polite interest as willingness to pay.

## North Star

`Relevant Tender Delivered -> Customer Took Action -> Bid/Quote Initiated`

Only after this funnel is demonstrated should Tender Radar become a broader SaaS product.
