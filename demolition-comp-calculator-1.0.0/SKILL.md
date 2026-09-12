---
name: 征收拆迁补偿测算器
slug: demolition-comp-calculator
displayName: 征收拆迁补偿测算器
display_name: 征收拆迁补偿测算器
description: 输入房屋面积、类似房地产市场价格、征收方报价、搬迁/临时安置/停产停业损失、补助奖励，以及可选的产权调换房屋单价面积，依据国务院令第590号与土地管理法第48条，做"货币补偿 vs 产权调换"三方案对比与第19条法定下限校验，并生成可打印的测算报告。本技能为支付宝 AI 按量，调用前需完成 402 账单支付。
tags: [征收拆迁, 拆迁补偿, 房屋征收, 产权调换, 货币补偿, 590号令, 土地管理法48, 补偿测算, 计算器, AI付, 按量, 402]
version: 1.0.0
capability: finance_calculation
deliverable:
  type: report
  formats: [html, pdf]
  name: 征收拆迁补偿测算报告
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

# 征收拆迁补偿测算器 (demolition-comp-calculator)

当用户说「拆迁补偿 / 征收补偿 / 房屋被征收能赔多少 / 货币补偿和产权调换哪个划算 / 征收方报价低于市场价 / 搬迁费临时安置费 / 停产停业损失 / 回迁房差价」时触发。

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

验付通过并生成《征收拆迁补偿测算报告》后，必须调用 **`alipay.aipay.agent.fulfillment.confirm`**（入参仅 `trade_no`）确认履约。确认成功后才将订单标记为最终 `FULFILLED` 并返回报告；确认失败允许同一 `Payment-Proof` 重试确认，避免资源已生成但平台未记录履约。

### 5. 订单持久化与幂等

返回 `Payment-Needed` 前，必须持久化 `out_trade_no`、`resource_id`、金额、状态、过期时间，确保付款后携带 `Payment-Proof` 回来时能映射回本地订单。同一订单重复携带 `Payment-Proof` 时**不得重复发放资源**：已原子进入待确认或已完成状态的同一订单，只重试确认或返回已保存结果。严格执行幂等履约，防止金额篡改、资源防串（`resource_id` 必须与验付结果一致）与重复履约。

> 支付相关的协议细节以 `alipay-aipay` 技能的 `aipay-interface-contract.md` 与 `checklist.md`「AI 按量付费专项校验」为准；本技能只实现 402 / `Payment-Needed` / `Payment-Proof` / `payment.verify` / `fulfillment.confirm`，不混入网页/移动应用收款的 `notify_url` 体系。

---

## 适用场景

面临征收拆迁时，绕不开的一个问题是"我到底能拿多少、货币补偿和回迁房哪个划算"。网上能查到的大多是原则性表述，落到自己身上就全模糊了：征收方报的单价比周边房价低，能不能拒；回迁房要补的差价怎么算；停产停业的损失找谁要；未经登记的那间房到底补不补。

这个技能把这几件事一次算清楚：

- **第 19 条法定下限校验**：拿征收方报价跟"类似房地产市场价格"比，低于下限的部分直接算成你可以主张的缺口
- **货币补偿 vs 产权调换三方案对比**：把两类方案的到手现金与折算总权益摆在一起，而不是只给一串孤立数字
- **未经登记建筑提示**（第 24 条）：提醒这部分的认定结果直接决定最终数额
- **生成可打印的测算报告**：含逐项金额、算式、依据条款与法律原文摘录

## 输入参数

| 参数 | 必填 | 说明 |
|---|---|---|
| `--area` | 是 | 合法建筑面积（㎡） |
| `--illegal-area` | 否 | 未经登记 / 涉嫌违法建筑面积（㎡），不计入补偿 |
| `--market-price` | 二选一 | 类似房地产市场价格（元/㎡） |
| `--offer-price` | 二选一 | 征收方提出的补偿单价（元/㎡） |
| `--moving-fee` | 否 | 搬迁费（元） |
| `--temp-monthly` | 否 | 临时安置费（元/月） |
| `--temp-months` | 否 | 过渡期限（月） |
| `--biz-profit` | 否 | 停产停业前月净利润（元/月，经营性用房） |
| `--biz-months` | 否 | 停产停业期限（月） |
| `--subsidy` | 否 | 补助和奖励（元） |
| `--swap-price` | 二选一 | 产权调换房屋单价（元/㎡） |
| `--swap-area` | 二选一 | 产权调换房屋面积（㎡） |
| `--land-type` | 否 | `state` 国有土地上房屋 / `collective` 集体土地征收 |

## 输出报告包含

1. 基本情况：合法面积、计算单价、被征收房屋价值
2. 法定下限校验（第 19 条）：报价是否低于类似房地产市场价格，低于则算出缺口
3. 方案 A 货币补偿：逐项金额与算式、依据条款
4. 方案 B 产权调换：差价结清、折算总权益
5. 方案对比：到手现金 vs 折算总权益，并指出两者性质不同
6. 未经登记建筑提示（第 24 条）
7. 测算说明与局限
8. 需要你核实的事项
9. 法律依据原文摘录

## 命令行用法

```bash
# 货币补偿，征收方报价低于市场价
python scripts/calculator.py --area 90 --market-price 18000 --offer-price 15000 \
    --moving-fee 3000 --temp-monthly 2000 --temp-months 24 --subsidy 50000

# 货币补偿 + 产权调换对比
python scripts/calculator.py --area 120 --market-price 16000 --offer-price 16500 \
    --moving-fee 4000 --temp-monthly 2500 --temp-months 30 --subsidy 80000 \
    --swap-price 15000 --swap-area 130

# 经营性用房 + 未经登记建筑 + 产权调换
python scripts/calculator.py --area 200 --illegal-area 30 --market-price 22000 --offer-price 20000 \
    --moving-fee 6000 --temp-monthly 3000 --temp-months 36 \
    --biz-profit 15000 --biz-months 6 --subsidy 100000 \
    --swap-price 19000 --swap-area 210

# 输出 HTML 报告
python scripts/calculator.py --area 90 --market-price 18000 --offer-price 15000 --html report.html
```

## 这个技能算不准的地方（必须如实告知用户）

- **第 19 条给的是下限，不是公式**：条例只规定补偿"不得低于类似房地产的市场价格"，具体价值由具有相应资质的房地产价格评估机构评估确定。不存在全国统一的补偿计算公式，本引擎只做下限校验与分项加总。
- **搬迁费、临时安置费、停产停业损失的标准由省级政府制定**（第 22、23 条）：各地差异极大，本引擎按你输入的参数计算，不内置任何地区标准。
- **产权调换房屋的价值取决于区位与市场行情**：两者性质不同——货币补偿是确定的现金，产权调换的价值随调换房屋行情波动，不可简单以数字大小论优劣。
- **评估时点与评估机构资质直接影响结果**：评估时点应为房屋征收决定公告之日。
- **集体土地适用《土地管理法》第 48 条而非 590 号令**：本引擎对集体土地只做结构提示，未做分项测算。

## 参考文件

- `formulas.md` — 公式逻辑、取值来源与"哪些地方没有公式"
- `examples.md` — 三个真实可复现样例（报价偏低 / 货币+调换对比 / 经营性+未经登记建筑）
- `disclaimer.md` — 免责声明与查证入口
- `scripts/calculator.py` — 测算引擎
- `scripts/report.py` — HTML 报告渲染
