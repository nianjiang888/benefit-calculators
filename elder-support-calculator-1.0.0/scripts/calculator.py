# -*- coding: utf-8 -*-
"""
赡养费测算引擎
==============

依据《中华人民共和国民法典》第26条、第1067条第2款及《中华人民共和国老年人
权益保障法》第14、15、19、20条测算。

**最重要的一件事，必须先说清楚：**

与抚养费不同（抚养费有《婚姻家庭编解释（一）》第49条明确的 20%~30% 比例区间），
**赡养费不存在任何法定计算公式，也没有法定比例**。现行法律只规定了给付义务的
成立要件（第1067条第2款：成年子女不履行赡养义务 + 父母缺乏劳动能力或者生活困难），
具体数额由人民法院综合当地生活水平、被赡养人实际需要、赡养人经济能力等因素确定。

因此本引擎的每一个算式都必须标注性质：
- 「法条要件」：义务是否成立（可依法条判断）
- 「实务惯例」：数额怎么算（无明文，来自裁判通行做法）

用法：
    python scripts/calculator.py --local-cost 2400 --dibao 680 \
        --elder-income 1500 --medical 800 --children 3 \
        --child-incomes 8000,5000,3000
    python scripts/calculator.py ... --html report.html
"""

import argparse
import os
import sys
from typing import Any, Dict, List

LAWS = [
    {"cite": "《民法典》第26条第2款",
     "text": "成年子女对父母负有赡养、扶助和保护的义务。"},
    {"cite": "《民法典》第1067条第2款",
     "text": "成年子女不履行赡养义务的，缺乏劳动能力或者生活困难的父母，有要求成年子女给付赡养费的权利。"},
    {"cite": "《老年人权益保障法》第14条",
     "text": "赡养人应当履行对老年人经济上供养、生活上照料和精神上慰藉的义务，照顾老年人的特殊需要。"
             "赡养人是指老年人的子女以及其他依法负有赡养义务的人。赡养人的配偶应当协助赡养人履行赡养义务。"},
    {"cite": "《老年人权益保障法》第15条",
     "text": "赡养人应当使患病的老年人及时得到治疗和护理；对经济困难的老年人，应当提供医疗费用。"
             "对生活不能自理的老年人，赡养人应当承担照料责任；不能亲自照料的，可以按照老年人的意愿"
             "委托他人或者养老机构等照料。"},
    {"cite": "《老年人权益保障法》第19条",
     "text": "赡养人不得以放弃继承权或者其他理由，拒绝履行赡养义务。赡养人不履行赡养义务，老年人有要求"
             "赡养人付给赡养费等权利。赡养人不得要求老年人承担力不能及的劳动。"},
    {"cite": "《老年人权益保障法》第20条",
     "text": "经老年人同意，赡养人之间可以就履行赡养义务签订协议。赡养协议的内容不得违反法律的规定和"
             "老年人的意愿。基层群众性自治组织、老年人组织或者赡养人所在单位监督协议的履行。"},
]


def parse_incomes(s: str, n: int) -> List[float]:
    if not s:
        return [0.0] * n
    parts = [p.strip() for p in s.split(",") if p.strip()]
    vals = []
    for p in parts:
        try:
            vals.append(float(p))
        except ValueError:
            raise SystemExit(f"--child-incomes 中存在非数字：「{p}」")
    if len(vals) != n:
        raise SystemExit(f"--child-incomes 提供了 {len(vals)} 个收入，与 --children {n} 不一致")
    if any(v < 0 for v in vals):
        raise SystemExit("--child-incomes 不能为负数")
    return vals


def calculate(a) -> Dict[str, Any]:
    dibao = float(a.dibao or 0)            # 当地月低保标准（判例常见参照）
    local_cost = float(a.local_cost or 0)  # 当地月人均消费支出（体面生活参照）
    elder_income = float(a.elder_income or 0)
    medical = float(a.medical or 0)
    n = int(a.children)
    incomes = parse_incomes(a.child_incomes, n)

    if n <= 0:
        raise SystemExit("错误：--children 必须大于 0")
    if dibao <= 0 and local_cost <= 0:
        raise SystemExit("错误：--dibao 与 --local-cost 至少要填一个，否则无法确定参照标准")

    # 一、需求测算：两档参照
    need_low = dibao + medical if dibao else None
    need_high = local_cost + medical if local_cost else None

    # 二、缺口（扣除老人自有收入）
    gap_low = max(0.0, need_low - elder_income) if need_low is not None else None
    gap_high = max(0.0, need_high - elder_income) if need_high is not None else None

    # 三、法条门槛校验（第1067条第2款）
    # 要件：成年子女不履行赡养义务 + 父母「缺乏劳动能力」或「生活困难」二者其一
    # 要件为「缺乏劳动能力」或「生活困难」，二者满足其一即可，故优先看声明
    if a.labor_lost or a.living_difficulty:
        reasons = []
        if a.labor_lost:
            reasons.append("缺乏劳动能力")
        if a.living_difficulty:
            reasons.append("生活困难")
        threshold_level = "满足给付要件"
        threshold_note = (f"已声明老人{'、'.join(reasons)}，满足第1067条第2款的给付要件之一"
                          f"（「缺乏劳动能力」与「生活困难」满足其一即可）。"
                          f"另一要件是「成年子女不履行赡养义务」，需就该事实举证。")
        if gap_low is not None and gap_low <= 0:
            threshold_note += ("注意：按保底档测算，老人自有收入已覆盖基本需求、不形成经济缺口，"
                               "按合理档测算仍有缺口。要件既已满足，法院可能在两档之间酌定数额，"
                               "也可能仅支持部分请求。")
    elif gap_low is not None and gap_low <= 0:
        threshold_note = (
            "按保底档测算，老人自有收入已能覆盖基本生活需求，未形成经济缺口，且未声明缺乏劳动能力。"
            "依第1067条第2款，给付赡养费请求权的成立要件之一是父母「缺乏劳动能力」或「生活困难」；"
            "若经济上并不困难，单纯要求给付金钱赡养费可能不被支持。"
            "但需强调：经济供养只是赡养义务的一部分，生活照料与精神慰藉义务不因此免除"
            "（《老年人权益保障法》第14条）。")
        threshold_level = "可能未达给付要件"
    else:
        threshold_note = (
            "未声明老人缺乏劳动能力或生活困难。依第1067条第2款，这是给付赡养费请求权的成立要件之一，"
            "需就「缺乏劳动能力」或「生活困难」二者其一举证（满足其一即可）。"
            "建议补充老人的劳动能力状况与收支情况。")
        threshold_level = "要件待举证"

    # 四、分摊：均摊 + 按能力加权
    def split(gap):
        if gap is None:
            return None
        equal = gap / n
        # 按能力加权：收入低于当地人均消费支出的，按 0.5 折算（体现其自身生活压力）
        # 这是实务惯例，法条无明文
        base_line = local_cost if local_cost > 0 else (dibao if dibao > 0 else 0)
        eff = []
        for inc in incomes:
            if base_line > 0 and inc < base_line:
                eff.append(inc * 0.5)
            else:
                eff.append(inc)
        s = sum(eff)
        if s <= 0:
            weighted = [equal] * n
            weight_note = "各子女收入均为 0 或未填，无法按能力加权，此处按人数均摊。"
        else:
            weighted = [gap * e / s for e in eff]
            weight_note = ("按子女收入能力加权分摊：收入低于当地人均消费支出水平的，其收入按 0.5 折算后参与加权，"
                           "以体现其自身生活压力。此折算系数为实务惯例，法条无明文。")
        return {"gap": gap, "equal": equal, "weighted": weighted, "weight_note": weight_note}

    split_low = split(gap_low)
    split_high = split(gap_high)

    items = []
    if need_low is not None:
        items.append({"name": "保底档月需求", "formula": f"低保标准 {dibao:,.0f} + 医疗护理 {medical:,.0f}",
                      "amount": need_low, "basis": "实务惯例：法院判决赡养费常参照当地城乡居民最低生活保障标准"})
    if need_high is not None:
        items.append({"name": "合理档月需求", "formula": f"人均消费支出 {local_cost:,.0f} + 医疗护理 {medical:,.0f}",
                      "amount": need_high, "basis": "实务惯例：参照当地居民人均消费支出，对应更体面的生活水平"})
    items.append({"name": "老人自有月收入", "formula": "养老金及其他收入",
                  "amount": -elder_income, "basis": "事实输入：计算缺口时应予扣除"})

    notes = [
        "**赡养费没有任何法定计算公式，也没有法定比例**。这与抚养费不同——抚养费有"
        "《婚姻家庭编解释（一）》第49条明确的 20%~30% 比例区间，赡养费没有。数额由人民法院"
        "综合当地生活水平、被赡养人实际需要、赡养人经济能力等因素确定。",
        "本引擎的「保底档 / 合理档」是两档参照口径，不是法律标准。保底档参照当地低保标准，"
        "对应司法实践中较常见的判决水平；合理档参照当地人均消费支出，对应更体面的生活水平。",
        "按能力加权的 0.5 折算系数属实务惯例，法条无明文。不同法院对低收入子女的处理差异较大，"
        "有些判决直接按人数均摊。",
        "大病医疗、长期护理、机构养老等大额支出，通常在基础赡养费之外另行主张与分担，"
        "本引擎将其计入「医疗护理」项后参与分摊，实际诉讼中可能单独列支。",
        "赡养义务包含经济供养、生活照料、精神慰藉三方面（《老年人权益保障法》第14条），"
        "金钱给付只是其中之一。不得以放弃继承权为由拒绝履行（第19条）。",
    ]
    if a.care_required:
        notes.append("已声明老人生活不能自理。依《老年人权益保障法》第15条，赡养人应当承担照料责任；"
                     "不能亲自照料的，可以按照老年人意愿委托他人或者养老机构照料，相关费用应计入赡养成本。")

    verify = [
        "当地最新的城乡居民最低生活保障标准、人均消费支出数据（分城镇/农村口径，差别很大）。",
        "老人的劳动能力状况与全部收入来源（养老金、租金、赡养以外的其他收入）。",
        "医疗护理支出的真实性与持续性（一次性大额支出与长期固定支出，法院处理不同）。",
        "各子女的真实收入与自身负担（本人及配偶、子女的生活、教育、医疗支出）。",
        "是否已形成赡养协议（《老年人权益保障法》第20条），协议内容不得违反法律与老年人意愿。",
        "是否存在子女无经济能力、自身为低保对象等特殊情形。",
    ]

    return {
        "dibao": dibao, "local_cost": local_cost, "elder_income": elder_income,
        "medical": medical, "children": n, "incomes": incomes,
        "need_low": need_low, "need_high": need_high,
        "gap_low": gap_low, "gap_high": gap_high,
        "split_low": split_low, "split_high": split_high,
        "threshold_level": threshold_level, "threshold_note": threshold_note,
        "items": items, "notes": notes, "verify": verify, "laws": LAWS,
        "care_required": a.care_required,
    }


def fmt(v) -> str:
    if v is None:
        return "—"
    return f"{float(v):,.2f}"


def print_text(r: Dict[str, Any]):
    print("=" * 78)
    print("赡养费测算报告")
    print("=" * 78)
    print("【一、月需求测算】")
    print(f"  保底档（低保 {fmt(r['dibao'])} + 医疗护理 {fmt(r['medical'])}）：{fmt(r['need_low'])} 元/月")
    print(f"  合理档（人均消费 {fmt(r['local_cost'])} + 医疗护理 {fmt(r['medical'])}）：{fmt(r['need_high'])} 元/月")
    print(f"  老人自有月收入：{fmt(r['elder_income'])} 元")
    print(f"  月缺口（保底档）：{fmt(r['gap_low'])} 元")
    print(f"  月缺口（合理档）：{fmt(r['gap_high'])} 元")
    print()
    print(f"【二、分摊结论】子女 {r['children']} 人")
    print(f"{'子女':<8}{'月收入':>12}{'均摊(保底)':>14}{'均摊(合理)':>14}{'按能力加权(合理)':>20}")
    print("-" * 78)
    sl, sh = r["split_low"], r["split_high"]
    for i, inc in enumerate(r["incomes"], 1):
        e_low = fmt(sl["equal"]) if sl else "—"
        e_high = fmt(sh["equal"]) if sh else "—"
        w_high = fmt(sh["weighted"][i - 1]) if sh else "—"
        print(f"第{i}位{'':<5}{fmt(inc):>12}{e_low:>14}{e_high:>14}{w_high:>20}")
    print("-" * 78)
    if sh:
        print(f"  合计（合理档按能力加权）：{fmt(sum(sh['weighted']))} 元/月")
        print(f"  {sh['weight_note']}")
    print()
    print("【三、法条门槛校验（第1067条第2款）】")
    print(f"  {r['threshold_level']}：{r['threshold_note']}")
    print()
    print("【四、说明与局限】")
    for n in r["notes"]:
        print(f"  · {n}")
    print()
    print("【五、需要你核实的事项】")
    for v in r["verify"]:
        print(f"  · {v}")
    print()
    print("本报告由 AI 依据公开法条测算生成，金额为区间参考值，不构成法律意见。")
    print("=" * 78)


def main():
    ap = argparse.ArgumentParser(
        description="赡养费测算器（民法典第1067条第2款 / 老年人权益保障法）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "注意：赡养费不存在法定计算公式，本引擎输出的是两档参照口径下的估算。\n\n"
            "示例：\n"
            "  python scripts/calculator.py --local-cost 2400 --dibao 680 \\\n"
            "      --elder-income 1500 --medical 800 --children 3 \\\n"
            "      --child-incomes 8000,5000,3000 --labor-lost\n"))
    ap.add_argument("--dibao", type=float, default=None, help="当地月最低生活保障标准（元/月）")
    ap.add_argument("--local-cost", type=float, default=None, help="当地月人均消费支出（元/月）")
    ap.add_argument("--elder-income", type=float, default=0, help="老人月自有收入（养老金等，元/月）")
    ap.add_argument("--medical", type=float, default=0, help="老人月均医疗/护理刚性支出（元/月）")
    ap.add_argument("--children", type=int, required=True, help="成年子女人数")
    ap.add_argument("--child-incomes", default="", help="各子女月收入，逗号分隔，如 8000,5000,3000")
    ap.add_argument("--labor-lost", action="store_true", help="老人缺乏劳动能力（第1067条第2款要件之一）")
    ap.add_argument("--living-difficulty", action="store_true", help="老人生活困难（第1067条第2款要件之一）")
    ap.add_argument("--care-required", action="store_true",
                    help="老人生活不能自理（触发《老年人权益保障法》第15条照料责任提示）")
    ap.add_argument("--html", nargs="?", const="elder-support-report.html", default=None,
                    help="输出 HTML 报告到指定路径（默认 elder-support-report.html）")
    a = ap.parse_args()

    r = calculate(a)
    print_text(r)

    if a.html:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from report import render_html, save_html
        save_html(render_html(r), a.html)
        print(f"\nHTML 报告已生成：{a.html}")


if __name__ == "__main__":
    main()
