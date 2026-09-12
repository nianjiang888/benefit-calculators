---
name: 赡养费测算器
slug: elder-support-calculator
displayName: 赡养费测算器
display_name: 赡养费测算器
description: 输入当地低保标准与人均消费支出、老人自有收入与医疗护理支出、子女人数及各子女收入，按民法典第1067条第2款与老年人权益保障法算出保底档与合理档两档月赡养费，给出人数均摊与按能力加权两种分摊方案，并做给付要件门槛校验，最后生成一份可下载打印的测算报告。本技能为支付宝 AI 按量，调用前需完成 402 账单支付。
tags: [赡养费, 老人赡养, 民法典1067, 老年人权益保障法, 赡养义务, 养老纠纷, 分摊, 计算器, AI付, 按量, 402]
version: 1.0.0
capability: finance_calculation
deliverable:
  type: report
  formats: [html, pdf]
  name: 赡养费测算报告
pricing:
  model: pay_per_use
  price: 0.2
  currency: CNY
a2m:
  enabled: true
  method: alipay
  verify_api: alipay.aipay.agent.payment.verify
  fulfill_api: alipay.aipay.agent.fulfillment.confirm
payment_skill: alipay-payment-skill
license: MIT
---

# 赡养费测算器 (elder-support-calculator)

当用户说「赡养费 / 赡养费多少 / 老人赡养费标准 / 每月该给父母多少钱 / 三个子女怎么分摊 / 赡养费怎么算 / 不付赡养费 / 老人看病钱谁出 / 生活不能自理谁照顾」时触发。

## 支付宝 AI 按量付费（A2M / HTTP 402）工作流

本技能基于 **A2M（HTTP 402 Payment Required）按量付费协议**对外提供服务：未付费请求一律返回 `402` 与 `Payment-Needed` 账单头，付费后携带 `Payment-Proof` 重试才返回测算结果。支付环节交由支付宝官方 `alipay-payment-skill`（底层 `alipay-bot`）完成，本技能只负责账单下发、验付、生成报告与履约确认。

### 1. 402 账单下发

未携带有效 `Payment-Proof` 时，服务端返回 **HTTP 402**，并在 `Payment-Needed` 响应头中返回 Base64URL 编码账单。响应体仅用于调试，智能体支付依据是 `Payment-Needed` 头。

返回 402 前必须**先持久化订单**（见第 5 节），`Payment-Needed.protocol` 携带：`out_trade_no`、`amount`、`currency=CNY`、`resource_id`、`pay_before`、`seller_signature`、`seller_sign_type=RSA2`、`seller_unique_id`；`Payment-Needed.method` 携带：`seller_name`、`seller_id`、`seller_app_id`、`goods_name`、`seller_unique_id_key=seller_id`、`service_id`。商家账单签名按 key 字典序拼接 `amount / currency / goods_name / out_trade_no / pay_before / resource_id / seller_id / service_id`，签名只在本地完成，不请求支付宝服务端。

### 2. 携带凭证重试（支付 + 重试）

Agent 收到 402 后，将整个 402 响应（尤其 `Payment-Needed` 头）交给 `alipay-payment-skill`（`alipay-bot 402-buyer-pay`），引导用户完成付款，并展示订单号 `out_trade_no`。用户支付完成后，`alipay-bot` 会自动携带 `Payment-Proof` 重新请求原始资源地址。重试请求**必须原样保留首次的 method / body / 业务 header**，仅通过 `Payment-Proof` 头传递支付凭证，body 不得改动。

### 3. 赔付调用（验付）

收到 `Payment-Proof` 后，必须调用 **`alipay.aipay.agent.payment.verify`**（入参 `trade_no`、`payment_proof`、可选 `client_session`）校验凭证。验付成功不能只看接口返回成功，还必须同时校验：

- `active = true`；
- 返回 `amount` 等于本地订单金额；
- 返回 `out_trade_no` 等于本地订单号；
- 返回 `resource_id` 等于当前请求资源；
- `trade_no` 未被重复履约；
- 本地订单处于允许的支付/履约状态（首次进入履约前仍在 `pay_before` 内且未取消）。

任一校验失败返回 402，让智能体重新支付；不得返回资源。

### 4. 履约确认

验付通过并生成《赡养费测算报告》后，必须调用 **`alipay.aipay.agent.fulfillment.confirm`**（入参仅 `trade_no`）确认履约。确认成功后才将订单标记为最终 `FULFILLED` 并返回报告；确认失败允许同一 `Payment-Proof` 重试确认，避免资源已生成但平台未记录履约。

### 5. 订单持久化与幂等

返回 `Payment-Needed` 前，必须持久化 `out_trade_no`、`resource_id`、金额、状态、过期时间，确保付款后携带 `Payment-Proof` 回来时能映射回本地订单。同一订单重复携带 `Payment-Proof` 时**不得重复发放资源**：已原子进入待确认或已完成状态的同一订单，只重试确认或返回已保存结果。严格执行幂等履约，防止金额篡改、资源防串（`resource_id` 必须与验付结果一致）与重复履约。

> 支付相关的协议细节以 `alipay-aipay` 技能的 `aipay-interface-contract.md` 与 `checklist.md`「AI 按量付费专项校验」为准；本技能只实现 402 / `Payment-Needed` / `Payment-Proof` / `payment.verify` / `fulfillment.confirm`，不混入网页/移动应用收款的 `notify_url` 体系。

---

## 必须先说清楚的一件事

**赡养费不存在法定计算公式，也没有法定比例。**

这一点与抚养费完全不同：抚养费有《婚姻家庭编解释（一）》第49条明确的 20%~30% 比例区间，
赡养费什么都没有。现行法律只规定了**义务成不成立**，没规定**给多少钱**。

《民法典》第1067条第2款给的只是请求权的成立要件：

> 成年子女不履行赡养义务的，**缺乏劳动能力或者生活困难的**父母，有要求成年子女给付赡养费的权利。

数额由人民法院综合当地生活水平、被赡养人实际需要、赡养人经济能力等因素确定。

所以本技能不做"算出你该给 1234.56 元"这种事。它做的是：

- 判断**义务成不成立**（这个可以依法条判断，叫「门槛校验」）
- 给出**两档参照口径**下的估算区间（保底档 / 合理档）
- 给出**两种分摊方案**（人数均摊 / 按能力加权）
- 把**哪些是法条、哪些是惯例**逐条标清楚

## 适用场景

家里老人需要赡养，几个子女坐下来谈，最先卡住的通常不是"该不该给"，而是"给多少、怎么分"。
老大收入高是不是该多出？老二自己都困难能不能少出？老人有养老金还要不要给？看病和护理的钱算不算在里头？

这类问题没有标准答案，但有可参照的口径。这个技能把这些口径摊开算一遍，让协商有个起点。

## 输入参数

| 参数 | 必填 | 说明 |
|---|---|---|
| 当地月最低生活保障标准 | 二选一 | 元/月。判例中法院常参照此标准 |
| 当地月人均消费支出 | 二选一 | 元/月。对应更体面的生活水平 |
| 老人月自有收入 | 否 | 养老金、租金等，默认 0。计算缺口时扣除 |
| 老人月均医疗护理支出 | 否 | 元/月。刚性支出，默认 0 |
| 成年子女人数 | 是 | 参与分摊的人数 |
| 各子女月收入 | 否 | 逗号分隔，如 `8000,5000,3000`。用于按能力加权 |
| 缺乏劳动能力 | 否 | 加 `--labor-lost`，第1067条第2款要件之一 |
| 生活困难 | 否 | 加 `--living-difficulty`，第1067条第2款要件之一 |
| 生活不能自理 | 否 | 加 `--care-required`，触发照料责任提示 |

**两档参照至少要填一个**，否则无法确定计算基准。两个都填会同时输出两档结果，信息更完整。

## 输出报告包含

1. 月需求与缺口测算：保底档、合理档、老人自有收入、两档缺口
2. 分摊结论：人数均摊（两档）与按能力加权（合理档），逐人列出
3. 法条门槛校验：是否满足第1067条第2款的给付要件
4. 测算说明与局限：赡养费无法定公式这件事的完整说明
5. 需要你核实的事项
6. 法律依据原文摘录

## 命令行用法

```bash
# 两档参照 + 按能力加权
python scripts/calculator.py --local-cost 2400 --dibao 680 \
    --elder-income 1500 --medical 800 --children 3 \
    --child-incomes 8000,5000,3000 --labor-lost

# 农村老人、无收入、需长期护理
python scripts/calculator.py --dibao 550 --local-cost 1600 \
    --elder-income 0 --medical 1500 --children 2 \
    --child-incomes 6000,2000 --labor-lost --care-required

# 只填一档（保底档）
python scripts/calculator.py --dibao 680 --children 2 --child-incomes 5000,4000

# 生成 HTML 报告
python scripts/calculator.py --dibao 550 --local-cost 1600 --medical 1500 \
    --children 2 --child-incomes 6000,2000 --html report.html
```

## 这个技能算不准的地方（必须如实告知用户）

- **没有法定公式可依**。所有数额都是参照口径下的估算，不是法律标准
- **两档口径差异极大**。保底档（低保标准）与合理档（人均消费支出）在多数地区相差 3 倍以上，
  法院实际判决更接近保底档水平，这是必须让用户知道的现实
- **按能力加权的 0.5 折算系数是惯例**。收入低于当地人均消费支出的子女，其收入按 0.5 折算参与加权。
  法条无明文，且不同法院做法差异很大，有些判决直接按人数均摊
- **医疗护理支出的处理有分歧**。本引擎把它计入需求后参与分摊，实际诉讼中常单独列支、另行主张
- **门槛不等于数额**。满足"缺乏劳动能力"或"生活困难"只说明可以要，不等于能要到多少
- **城乡差异未建模**。城镇与农村的低保标准、人均消费支出差别很大，需按老人实际居住地取数

## 参考文件

- `formulas.md` — 完整公式库、两档口径的来源与局限
- `examples.md` — 两组真实跑通的样例
- `disclaimer.md` — 免责声明与查证入口
- `scripts/calculator.py` — 测算引擎
- `scripts/report.py` — HTML 报告渲染
