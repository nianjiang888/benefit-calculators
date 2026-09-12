---
name: 遗产继承分配测算器
slug: inheritance-calculator
displayName: 遗产继承分配测算器
display_name: 遗产继承分配测算器
description: 输入遗产总额、是否夫妻共同财产、债务、各顺序继承人数及各自的分配情形（均等/应予照顾/可多分/应少分/不分），按民法典继承编第1127、1130、1153、1155、1159、1161条算出可分配净额与各继承人的份额区间，并做必留份校验与债务清偿上限提示，最后生成一份可下载打印的分配测算报告。本技能为支付宝 AI 按量，调用前需完成 402 账单支付。
tags: [遗产继承, 法定继承, 继承份额, 民法典1130, 必留份, 代位继承, 胎儿保留份, 计算器, AI付, 按量, 402]
version: 1.0.0
capability: finance_calculation
deliverable:
  type: report
  formats: [html, pdf]
  name: 遗产继承分配测算报告
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

# 遗产继承分配测算器 (inheritance-calculator)

当用户说「遗产怎么分 / 继承份额 / 法定继承 / 遗产分配比例 / 配偶能分多少 / 子女继承份额 / 父母有没有继承权 / 遗产要不要先还债 / 必留份 / 胎儿继承份额 / 多尽了赡养义务能多分吗」时触发。

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

验付通过并生成《遗产继承分配测算报告》后，必须调用 **`alipay.aipay.agent.fulfillment.confirm`**（入参仅 `trade_no`）确认履约。确认成功后才将订单标记为最终 `FULFILLED` 并返回报告；确认失败允许同一 `Payment-Proof` 重试确认，避免资源已生成但平台未记录履约。

### 5. 订单持久化与幂等

返回 `Payment-Needed` 前，必须持久化 `out_trade_no`、`resource_id`、金额、状态、过期时间，确保付款后携带 `Payment-Proof` 回来时能映射回本地订单。同一订单重复携带 `Payment-Proof` 时**不得重复发放资源**：已原子进入待确认或已完成状态的同一订单，只重试确认或返回已保存结果。严格执行幂等履约，防止金额篡改、资源防串（`resource_id` 必须与验付结果一致）与重复履约。

> 支付相关的协议细节以 `alipay-aipay` 技能的 `aipay-interface-contract.md` 与 `checklist.md`「AI 按量付费专项校验」为准；本技能只实现 402 / `Payment-Needed` / `Payment-Proof` / `payment.verify` / `fulfillment.confirm`，不混入网页/移动应用收款的 `notify_url` 体系。

---

## 适用场景

亲人过世后最先冒出来的问题通常是：这房子、这存款到底怎么分？是不是配偶先拿一半？欠的债要不要先还？一直照顾老人的是不是能多分？常年不露面的那个是不是就该少分？

这类问题看上去都有标准答案，实际每一条都有前提：

- **是不是夫妻共同财产**，直接决定遗产基数是全部还是一半（第1153条）
- **有没有债务**，决定可分配净额，而且清偿以遗产实际价值为限（第1159、1161条）
- **同一顺序几个人**，决定基础份额是几分之一（第1127、1130条）
- **各自的情形**，决定要不要调整（第1130条各款）

这个技能把这些前提逐个问清楚，然后按权重法算出份额——**给区间，不给假精确值**，并且每条结论都标明是法条明文还是实务惯例。

## 输入参数

| 参数 | 必填 | 说明 |
|---|---|---|
| 遗产总额 | 是 | 元。指被继承人死亡时遗留的财产总额（尚未扣除配偶份额与债务） |
| 是否夫妻共同财产 | 否 | `yes` 时先分出配偶一半（第1153条）；默认 `no` |
| 债务合计 | 否 | 被继承人依法应缴纳的税款和债务，默认 0 |
| 配偶人数 | 否 | 0 或 1 |
| 子女人数 | 否 | 含婚生、非婚生、养子女、有扶养关系的继子女 |
| 父母人数 | 否 | 0、1 或 2 |
| 胎儿数 | 否 | 保留份（第1155条） |
| 兄弟姐妹人数 | 否 | 无第一顺序继承人时才参与 |
| 祖父母外祖父母人数 | 否 | 无第一顺序继承人时才参与 |
| 各类别分配情形 | 否 | `normal` 均等 / `care` 应予照顾 / `support` 可多分 / `neglect` 应少分 / `exclude` 不分 |
| 组内细分 | 否 | 格式 `情形=人数[,情形=人数]`，如 `--children-spec "support=1,neglect=1"` |
| 存在必留份继承人 | 否 | 加 `--must-keep` 触发第1141条校验 |

**第一顺序只要有人，第二顺序就不参与**（第1127条第2款），引擎自动处理，不用你判断。

## 输出报告包含

1. 可分配遗产基数：总额、配偶先分、债务清偿、净额，每步附条款依据
2. 分配结论：各继承人人数、适用情形、基准份额、每人基准金额、每人区间
3. 份额调整依据：倍数区间 + 法条明文/惯例估算的明确区分
4. 必留份校验：第1141条与《继承编解释（一）》第25条
5. 测算说明与局限：哪些是法条、哪些是惯例、区间怎么算的
6. 需要你核实的事项
7. 法律依据原文摘录

## 命令行用法

```bash
# 标准均分：遗产120万，夫妻共有，配偶1+子女2+父母2，债务10万
python scripts/calculator.py --estate 1200000 --marital yes \
    --spouse 1 --children 2 --parents 2 --debts 100000

# 组内细分：子女2人中1人尽主要扶养义务（可多分）、1人有能力不尽义务（应少分）
python scripts/calculator.py --estate 800000 --children 2 \
    --children-spec "support=1,neglect=1"

# 第二顺序：无配偶子女父母，兄弟姐妹2人+祖父母1人
python scripts/calculator.py --estate 300000 --spouse 0 --children 0 --parents 0 \
    --siblings 2 --grandparents 1

# 胎儿保留份
python scripts/calculator.py --estate 2000000 --marital yes \
    --spouse 1 --children 1 --fetus 1 --parents 2

# 生成 HTML 报告
python scripts/calculator.py --estate 1200000 --marital yes \
    --spouse 1 --children 2 --parents 2 --html report.html
```

## 这个技能算不准的地方（必须如实告知用户）

- **第1130条没有给任何比例数字**。法条只说"一般应当均等""可以"多分、"应当"不分或者少分。报告里的调整幅度（照顾/多分 1.1~1.3 倍、少分 0.5~0.8 倍）是实务惯例估算，**不是法条标准**，法院未必采纳
- **「必要份额」的数额无法计算**。第1141条只要求保留"必要的遗产份额"，具体数额由人民法院按实际情况确定，本技能只能做定性提示
- **不处理遗嘱的具体分配**。有合法有效遗嘱的按遗嘱（第1123条），本技能算的是法定继承下的份额，遗嘱情形仅做必留份提示
- **代位继承与转继承只按你输入的人数计算**。第1128条的代位、第1152条的转继承需要你自行确认并计入人数
- **债务性质未区分**。夫妻共同债务、担保责任的划分会显著影响可分配基数，引擎按总额扣除，需你核实
- **份额是相对值**。全员适用同一系数时，归一化后比例与均分一致，这是数学必然，不是调整失效

## 参考文件

- `formulas.md` — 完整公式库、权重法推导与条款依据
- `examples.md` — 四组真实跑通的样例
- `disclaimer.md` — 免责声明与查证入口
- `scripts/calculator.py` — 测算引擎
- `scripts/report.py` — HTML 报告渲染
