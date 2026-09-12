---
name: 抚养费测算器
slug: child-support-calculator
displayName: 抚养费测算器
display_name: 抚养费测算器
description: 输入支付方收入、收入类型、需负担子女数与子女年龄，按民法典及婚姻家庭编解释（一）第49条的比例区间算出每月抚养费的低值、基准、高值三档，并做一次"够不够当地生活水平"的充足性校验，同时给出一次性给付参考与给付期限说明，最后生成一份可下载打印的测算报告。本技能为支付宝 AI 按量，调用前需完成 402 账单支付。
tags: [抚养费, 离婚, 子女抚养, 民法典1085, 婚姻家庭编解释一, 抚养费标准, 一次性给付, 计算器, AI付, 按量, 402]
version: 1.0.0
capability: finance_calculation
deliverable:
  type: report
  formats: [html, pdf]
  name: 抚养费测算报告
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

# 抚养费测算器 (child-support-calculator)

当用户说「抚养费 / 抚养费多少 / 离婚孩子抚养费 / 抚养费标准 / 一个月给多少抚养费 / 抚养费能不能涨 / 一次性抚养费 / 抚养费给到几岁 / 两个孩子抚养费」时触发。

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

验付通过并生成《抚养费测算报告》后，必须调用 **`alipay.aipay.agent.fulfillment.confirm`**（入参仅 `trade_no`）确认履约。确认成功后才将订单标记为最终 `FULFILLED` 并返回报告；确认失败允许同一 `Payment-Proof` 重试确认，避免资源已生成但平台未记录履约。

### 5. 订单持久化与幂等

返回 `Payment-Needed` 前，必须持久化 `out_trade_no`、`resource_id`、金额、状态、过期时间，确保付款后携带 `Payment-Proof` 回来时能映射回本地订单。同一订单重复携带 `Payment-Proof` 时**不得重复发放资源**：已原子进入待确认或已完成状态的同一订单，只重试确认或返回已保存结果。严格执行幂等履约，防止金额篡改、资源防串（`resource_id` 必须与验付结果一致）与重复履约。

> 支付相关的协议细节以 `alipay-aipay` 技能的 `aipay-interface-contract.md` 与 `checklist.md`「AI 按量付费专项校验」为准；本技能只实现 402 / `Payment-Needed` / `Payment-Proof` / `payment.verify` / `fulfillment.confirm`，不混入网页/移动应用收款的 `notify_url` 体系。

---

## 适用场景

离婚或分居时，绕不开的一个数是"不直接带孩子的一方每月该给多少"。网上流传的说法大多是一句"工资的 20% 到 30%"，听着简单，落到自己身上就全模糊了：工资算应发还是实发？两个孩子怎么提？当地消费水平低，按比例算出来够不够花？

这个技能把这几件事一次算清楚：

- 按比例区间算出**低值 / 基准 / 高值**三档，而不是假装能算出唯一正确的数字
- 做一次**充足性校验**：拿算出的金额跟"当地月人均消费支出的一半"比，明显偏低会直接提示这属于可以请求增加的法定情形
- 算清**一次性给付**到 18 周岁的总额，并说明为什么这个数只能当上限看
- 说清**给到几岁**、什么情况下 16 岁就能停、什么情况下 18 岁以后还得给

## 输入参数

| 参数 | 必填 | 说明 |
|---|---|---|
| 收入类型 | 是 | `fixed` 固定收入 / `annual` 无固定收入按年总收入 / `industry` 参照同行业平均 |
| 支付方月总收入 | 二选一 | 固定收入时填。指工资、奖金、津贴、补贴等全部收入 |
| 支付方年总收入 | 二选一 | 无固定收入时填，引擎自动 ÷12 折算月均 |
| 同行业平均月收入 | 二选一 | 无固定收入且无法举证时填，需注明来源 |
| 需负担子女数 | 否 | 默认 1。这个数决定比例区间能不能上调 |
| 子女当前年龄 | 是 | 周岁，可带小数。用于算剩余给付月数 |
| 当地月人均消费支出 | 否 | 强烈建议填。不填就跳过充足性校验 |

## 输出报告包含

1. 测算结论：收入基数、比例区间、月抚养费三档、一次性给付参考
2. 逐项金额与算式：每一档的算式和依据条款
3. 充足性校验：参照值、比值、结论、对应法条
4. 给付期限：剩余月数、16 周岁例外、成年子女例外
5. 测算说明与局限：哪些地方是法条明文、哪些是实务惯例
6. 需要你核实的事项
7. 法律依据原文摘录

## 命令行用法

```bash
# 固定收入
python scripts/calculator.py --income 12000 --children 1 --child-age 8 --local-cost 3200

# 无固定收入（按年总收入）
python scripts/calculator.py --annual-income 150000 --children 1 --child-age 6 --local-cost 3000

# 参照同行业平均
python scripts/calculator.py --industry-income 8000 --children 2 --child-age 4

# 输出 JSON 与 HTML 报告
python scripts/calculator.py --income 12000 --child-age 8 --local-cost 3200 --json
python scripts/calculator.py --income 12000 --child-age 8 --local-cost 3200 --html report.html
```

## 这个技能算不准的地方（必须如实告知用户）

- **月总收入口径不统一**：有的法院按应发工资，有的按实发，直接影响结果
- **两孩以上的比例没有法条明文**：第 49 条只说"可适当提高、一般不超 50%"，本技能的 30%~40%、40%~50% 是实务惯例，不是硬性标准
- **一次性给付支持率不高**：第 50 条要求"有条件"，实务中法院常不支持，即便支持也可能因资金时间价值有所折让
- **地方差异大**：经济发达地区法院常在比例之外另行考虑实际开销，本技能只做通用测算
- **大额教育、医疗通常另行主张**：固定抚养费里包含常规的教育医疗费，但私立学校、长期治疗这类大额支出，实务中另行分担（各半居多）

## 参考文件

- `formulas.md` — 完整公式库与条款依据
- `examples.md` — 三档样例（标准 / 低收入多孩 / 成年子女延长）
- `disclaimer.md` — 免责声明与查证入口
- `scripts/calculator.py` — 测算引擎
- `scripts/report.py` — HTML 报告渲染
