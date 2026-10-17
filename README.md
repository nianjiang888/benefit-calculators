# 权益测算计算器

抚养费 / 遗产 / 赡养 / 征收拆迁 四类法定权益测算器，依据公开法条做区间测算与方案对比。

共 **4** 个技能包，全部自包含（包内即可跑通，无需额外依赖）。

## 技能一览

| # | 技能包 | 名称 | 做什么 |
|---|---|---|---|
| 1 | `child-support-calculator-1.0.0` | 抚养费测算器 | 输入支付方收入、收入类型、需负担子女数与子女年龄，按民法典及婚姻家庭编解释（一）第49条的比例区间算出每月抚养费的低… |
| 2 | `demolition-comp-calculator-1.0.0` | 征收拆迁补偿测算器 | 输入房屋面积、类似房地产市场，以及可选的产权调换房屋单价面积，依据国务院令第590号与土地管理法第48条，做"货币补… |
| 3 | `elder-support-calculator-1.0.0` | 赡养费测算器 | 输入当地低保标准与人均消费支出、老人自有收入与医疗护理支出、子女人数及各子女收入，按民法典第1067条第2款与老年人… |
| 4 | `inheritance-calculator-1.0.0` | 遗产继承分配测算器 | 输入遗产总额、是否夫妻共同财产、债务、各顺序继承人数及各自的分配情形（均等/应予照顾/可多分/应少分/不分），按民法… |

## 目录结构

```
benefit-calc/
├── child-support-calculator-1.0.0/
├── demolition-comp-calculator-1.0.0/
├── elder-support-calculator-1.0.0/
├── inheritance-calculator-1.0.0/
├── ...（共 4 个技能目录）
```

每个技能包结构一致：`SKILL.md`（技能定义）、`scripts/`（引擎与冒烟测试）、`resources/`（规则与数据）、`references/`（依据）、`examples/`（输入输出样例）、`README.md`、`FAQ.md`、`CHANGELOG.md`。

## 本地使用

```
git clone <仓库地址>
```

把需要的技能目录整体复制到你的 Agent skills 目录即可。单个技能这样跑：

```
python <技能目录>/scripts/<引擎>.py --help
```

## 从 GitHub 导入到 SkillHub

每个技能独立目录，目录根即 `SKILL.md`，不含二进制文件。在 SkillHub 发布页选「从 GitHub 导入」，绑定账号后会自动扫出候选技能。

**注意：平台单次最多导入 5 个技能，4 个需要分 1 批。**

## 许可

MIT

## 出品方与更多工具

本技能系列由墨金格团队出品。主产品[墨金格](https://www.mojinge.cloud)（mojinge.cloud）——把故事变成短剧：一句想法进来，一部能拍的剧本出去，分集剧情、人物 / 场景 / 道具资产、每集分镜提示词一次给齐；导入小说可走全流程改编（导入 → 故事中枢 → 分集大纲 → 改编剧本 → 分镜脚本）。按次付费，生成失败不扣费，邮箱即账号。

Made by the team behind [Mojinge](https://www.mojinge.cloud) — turn a story into a shootable screenplay: episode breakdowns, character/scene/prop assets, and per-shot prompts in one pass.

配套开源件 [ShotLock](https://github.com/nianjiang888/shotlock)：分镜脚本一致性校验引擎，十五条规则专抓角色漂移、越轴、语速超载，可作生成流程的卡口。
