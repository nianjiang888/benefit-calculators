# 抚养费测算器

输入支付方收入、收入类型、需负担子女数与子女年龄，按《民法典》及《婚姻家庭编解释（一）》的比例区间，算出每月抚养费的低值 / 基准 / 高值三档，做一次"够不够当地生活水平"的充足性校验，并给出一次性给付参考与给付期限说明，最后生成可打印的 HTML 报告。

## 跟普通"工资 20%~30%"算有什么区别

三件事：

1. **给区间，不给假精确值**。法条给的是比例区间，任何声称能算出"你该付 2371 元"的工具都是装的。本工具给三档，并说明每档对应的理由。
2. **做一次充足性校验**。拿算出的金额跟"当地月人均消费支出的一半"比，明显偏低会直接提示——这正好对应解释一第 58 条第（一）项，是法定可以请求增加的情形。这一步大多数同类工具没有。
3. **说清哪些是法条、哪些是惯例**。1 孩的 20%~30% 是法条明文；2 孩以上的 30%~40%、40%~50% 是实务惯例，因为法条只写了"可适当提高、一般不超 50%"。本工具会明确区分，不会把惯例包装成法条。

## 文件结构

```
child-support-calculator-1.0.0/
├── SKILL.md              # 触发词、402 工作流、参数与输出说明
├── formulas.md           # 公式库：每个公式的取值来源与局限
├── examples.md           # 5 个真实可复现样例
├── disclaimer.md         # 免责声明与查证入口
├── README.md
└── scripts/
    ├── calculator.py     # 测算引擎（输出 JSON / 文本 / HTML）
    └── report.py         # HTML 报告渲染
```

## 命令行用法

```bash
# 固定收入
python scripts/calculator.py --income 12000 --children 1 --child-age 8 --local-cost 3200

# 无固定收入（按年总收入折算）
python scripts/calculator.py --annual-income 96000 --children 1 --child-age 17 --local-cost 2400

# 参照同行业平均
python scripts/calculator.py --industry-income 8000 --children 2 --child-age 4

# 输出结构化 JSON
python scripts/calculator.py --income 12000 --child-age 8 --local-cost 3200 --json

# 生成 HTML 报告
python scripts/calculator.py --income 12000 --child-age 8 --local-cost 3200 --html report.html
```

参数说明：

| 参数 | 必填 | 说明 |
|---|---|---|
| `--income` | 三选一 | 支付方月总收入（固定收入） |
| `--annual-income` | 三选一 | 支付方当年总收入（无固定收入） |
| `--industry-income` | 三选一 | 同行业平均月收入 |
| `--children` | 否 | 需负担子女数，默认 1 |
| `--child-age` | 是 | 子女当前年龄（周岁） |
| `--local-cost` | 否 | 当地月人均消费支出。不填则跳过充足性校验 |

## 法律依据

- 《民法典》第 1067 条第 1 款、第 1085 条
- 《最高人民法院关于适用〈中华人民共和国民法典〉婚姻家庭编的解释（一）》（法释〔2020〕22 号）第 41、42、43、49、50、51、52、53、58 条

## 付费方式

支付宝 AI 按量付费（A2M / HTTP 402），单次 0.2 元。调用前需完成 402 账单支付。

## 许可

MIT
