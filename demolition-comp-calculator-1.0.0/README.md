# 征收拆迁补偿测算器

输入房屋面积、类似房地产市场价格、征收方报价、搬迁 / 临时安置 / 停产停业损失、补助奖励，以及可选的产权调换房屋单价面积，依据国务院令第 590 号与《土地管理法》第 48 条，做"货币补偿 vs 产权调换"三方案对比与第 19 条法定下限校验，并生成可打印的 HTML 报告。

## 跟普通"补偿计算器"有什么区别

一个核心前提：**第 19 条给的是法定下限，不是补偿公式**。条例只规定补偿"不得低于类似房地产的市场价格"，具体价值由评估机构评估确定，不存在全国统一的补偿计算公式。所以本工具不做"算出你该拿多少"这种伪精确，而是做两件真正有用的事：

1. **第 19 条法定下限校验**。拿征收方报价跟"类似房地产市场价格"比，低于下限的部分直接算成你可以主张的缺口——这是大多数同类工具没有的一步。
2. **货币补偿 vs 产权调换两方案对比**。把到手现金与折算总权益摆在一起，并明确提示两种方案性质不同，不能简单以数字大小论优劣。

另外，搬迁费、临时安置费、停产停业损失的标准由省级政府制定，各地差异极大，本引擎按你输入的参数计算，不内置任何地区标准。

## 文件结构

```
demolition-comp-calculator-1.0.0/
├── SKILL.md              # 触发词、402 工作流、参数与输出说明
├── formulas.md           # 公式逻辑：哪些地方有算式、哪些地方根本没有公式
├── examples.md           # 3 个真实可复现样例
├── disclaimer.md         # 免责声明与查证入口
├── README.md
└── scripts/
    ├── calculator.py     # 测算引擎（输出文本 / HTML）
    └── report.py         # HTML 报告渲染
```

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

参数说明：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `--area` | 是 | 合法建筑面积（㎡） |
| `--market-price` | 二选一 | 类似房地产市场价格（元/㎡） |
| `--offer-price` | 二选一 | 征收方提出的补偿单价（元/㎡） |
| `--moving-fee` | 否 | 搬迁费（元） |
| `--temp-monthly` / `--temp-months` | 否 | 临时安置费（元/月）与过渡期限（月） |
| `--biz-profit` / `--biz-months` | 否 | 停产停业月净利润与期限（经营性用房） |
| `--subsidy` | 否 | 补助和奖励（元） |
| `--swap-price` / `--swap-area` | 二选一 | 产权调换房屋单价（元/㎡）与面积（㎡） |
| `--illegal-area` | 否 | 未经登记 / 涉嫌违法建筑面积（不计入补偿） |
| `--land-type` | 否 | `state` 国有 / `collective` 集体土地（默认国有） |

## 法律依据

- 《国有土地上房屋征收与补偿条例》（国务院令第 590 号）第 2、17、19、21、22、23、24、26、27 条
- 《中华人民共和国土地管理法》（2019 年修正）第 48 条

## 付费方式

支付宝 AI 按量付费（A2M / HTTP 402），单次 0.2 元。调用前需完成 402 账单支付。

## 许可

MIT
