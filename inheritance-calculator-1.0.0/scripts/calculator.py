# -*- coding: utf-8 -*-
"""
遗产继承分配测算引擎
====================

依据《中华人民共和国民法典》继承编（第1122、1123、1126、1127、1128、1129、1130、
1141、1152、1153、1154、1155、1159、1161条）及《最高人民法院关于适用〈中华人民
共和国民法典〉继承编的解释（一）》（法释〔2020〕23号）第14条、第25条测算。

设计原则（与本项目其他测算器一致）：
1. **给区间，不给假精确值**。第1130条只规定"一般应当均等""可以"多分、
   "应当"不分或者少分，**法条没有给出任何比例数字**。凡涉及调整幅度的
   系数一律标注为"实务惯例估算"，不包装成法条。
2. **法条明文与实务惯例分开标注**。每条输出的 basis 都标明是"法条"还是"惯例"。
3. **可解释**。份额用权重法计算并归一化，保证同一顺序内份额之和恒为 100%，
   每一步都能手工复核。
4. **支持组内细分**。同一类别（如子女）内部不同继承人可适用不同情形，
   这是继承纠纷最常见的形态。

用法：
    python scripts/calculator.py --estate 1200000 --marital yes \
        --spouse 1 --children 2 --parents 2 --debts 100000
    python scripts/calculator.py --estate 800000 --children 2 \
        --children-spec "support=1,neglect=1"
    python scripts/calculator.py ... --html report.html
"""

import argparse
import sys
from typing import Any, Dict, List, Optional

# 调整系数：法条只定性不定量，以下幅度为实务惯例估算
# 来源：第1130条各款的定性表述（照顾/多分/少分/不分），幅度无明文
FACTORS = {
    "normal":  {"low": 1.0, "base": 1.0, "high": 1.0,
                "label": "一般情形（均等）",
                "basis": "《民法典》第1130条第1款（法条：一般应当均等）"},
    "care":    {"low": 1.1, "base": 1.2, "high": 1.3,
                "label": "生活特殊困难又缺乏劳动能力（予以照顾）",
                "basis": "《民法典》第1130条第2款（法条：应当予以照顾；幅度为惯例估算）"},
    "support": {"low": 1.1, "base": 1.2, "high": 1.3,
                "label": "尽了主要扶养义务或与被继承人共同生活（可以多分）",
                "basis": "《民法典》第1130条第3款（法条：可以多分；幅度为惯例估算）"},
    "neglect": {"low": 0.5, "base": 0.6, "high": 0.8,
                "label": "有扶养能力和条件但不尽扶养义务（不分或者少分）",
                "basis": "《民法典》第1130条第4款（法条：应当不分或者少分；幅度为惯例估算）"},
    "exclude": {"low": 0.0, "base": 0.0, "high": 0.0,
                "label": "不分（严重情形，按用户指定）",
                "basis": "《民法典》第1130条第4款（法条：应当不分）"},
}

LAWS = [
    {"cite": "《民法典》第1122条",
     "text": "遗产是自然人死亡时遗留的个人合法财产。依照法律规定或者根据其性质不得继承的遗产，不得继承。"},
    {"cite": "《民法典》第1123条",
     "text": "继承开始后，按照法定继承办理；有遗嘱的，按照遗嘱继承或者遗赠办理；有遗赠扶养协议的，按照协议办理。"},
    {"cite": "《民法典》第1127条第1、2款",
     "text": "遗产按照下列顺序继承：（一）第一顺序：配偶、子女、父母；（二）第二顺序：兄弟姐妹、祖父母、外祖父母。"
             "继承开始后，由第一顺序继承人继承，第二顺序继承人不继承；没有第一顺序继承人继承的，由第二顺序继承人继承。"},
    {"cite": "《民法典》第1128条",
     "text": "被继承人的子女先于被继承人死亡的，由被继承人的子女的直系晚辈血亲代位继承。"
             "被继承人的兄弟姐妹先于被继承人死亡的，由被继承人的兄弟姐妹的子女代位继承。"
             "代位继承人一般只能继承被代位继承人有权继承的遗产份额。"},
    {"cite": "《民法典》第1130条",
     "text": "同一顺序继承人继承遗产的份额，一般应当均等。对生活有特殊困难又缺乏劳动能力的继承人，分配遗产时，"
             "应当予以照顾。对被继承人尽了主要扶养义务或者与被继承人共同生活的继承人，分配遗产时，可以多分。"
             "有扶养能力和有扶养条件的继承人，不尽扶养义务的，分配遗产时，应当不分或者少分。"
             "继承人协商同意的，也可以不均等。"},
    {"cite": "《民法典》第1141条",
     "text": "遗嘱应当为缺乏劳动能力又没有生活来源的继承人保留必要的遗产份额。"},
    {"cite": "《民法典》第1153条第1款",
     "text": "夫妻共同所有的财产，除有约定的外，遗产分割时，应当先将共同所有的财产的一半分出为配偶所有，"
             "其余的为被继承人的遗产。"},
    {"cite": "《民法典》第1155条",
     "text": "遗产分割时，应当保留胎儿的继承份额。胎儿娩出时是死体的，保留的份额按照法定继承办理。"},
    {"cite": "《民法典》第1159条",
     "text": "分割遗产，应当清偿被继承人依法应当缴纳的税款和债务；但是，应当为缺乏劳动能力又没有生活来源的"
             "继承人保留必要的遗产。"},
    {"cite": "《民法典》第1161条第1、2款",
     "text": "继承人以所得遗产实际价值为限清偿被继承人依法应当缴纳的税款和债务。超过遗产实际价值部分，"
             "继承人自愿偿还的不在此限。继承人放弃继承的，对被继承人依法应当缴纳的税款和债务可以不负清偿责任。"},
    {"cite": "《继承编解释（一）》第25条",
     "text": "遗嘱人未保留缺乏劳动能力又没有生活来源的继承人的遗产份额，遗产处理时，应当为该继承人留下必要的"
             "遗产，所剩余的部分，才可参照遗嘱确定的分配原则处理。继承人是否缺乏劳动能力又没有生活来源，"
             "应按遗嘱生效时该继承人的具体情况确定。"},
]


def parse_spec(spec: Optional[str], total: int, label: str, default_kind: str) -> List[Dict]:
    """解析组内细分，如 "support=1,neglect=1"。剩余人数归入 default_kind。"""
    if not spec:
        return [{"kind": default_kind, "count": total}]
    parts, used = [], 0
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise SystemExit(f"--spec 格式错误（{label}）：「{item}」应为 情形=人数，如 support=1")
        k, v = item.split("=", 1)
        k = k.strip().lower()
        if k not in FACTORS:
            raise SystemExit(f"--spec 未知情形（{label}）：「{k}」，可选 {', '.join(FACTORS)}")
        try:
            c = int(v.strip())
        except ValueError:
            raise SystemExit(f"--spec 人数不是整数（{label}）：「{v}」")
        if c <= 0:
            raise SystemExit(f"--spec 人数必须为正（{label}）：「{k}={c}」")
        parts.append({"kind": k, "count": c})
        used += c
    if used > total:
        raise SystemExit(f"--spec 细分人数合计 {used} 超过 {label} 总人数 {total}")
    if used < total:
        parts.append({"kind": default_kind, "count": total - used})
    return parts


def build_heir_groups(a) -> List[Dict[str, Any]]:
    """构造继承人分组。第一顺序有人时，第二顺序不参与继承（第1127条第2款）。"""
    first = []
    if a.spouse:
        first.append({"key": "spouse", "label": "配偶", "count": a.spouse,
                      "parts": parse_spec(a.spouse_spec, a.spouse, "配偶", a.spouse_kind)})
    if a.children:
        first.append({"key": "children", "label": "子女", "count": a.children,
                      "parts": parse_spec(a.children_spec, a.children, "子女", a.children_kind)})
    if a.parents:
        first.append({"key": "parents", "label": "父母", "count": a.parents,
                      "parts": parse_spec(a.parents_spec, a.parents, "父母", a.parents_kind)})
    if a.fetus:
        first.append({"key": "fetus", "label": "胎儿（保留份）", "count": a.fetus,
                      "parts": [{"kind": "normal", "count": a.fetus}]})

    if first:
        return first, "第一顺序（配偶、子女、父母）"

    second = []
    if a.siblings:
        second.append({"key": "siblings", "label": "兄弟姐妹", "count": a.siblings,
                       "parts": parse_spec(a.siblings_spec, a.siblings, "兄弟姐妹", a.siblings_kind)})
    if a.grandparents:
        second.append({"key": "grandparents", "label": "祖父母、外祖父母", "count": a.grandparents,
                       "parts": parse_spec(a.grandparents_spec, a.grandparents,
                                           "祖父母外祖父母", a.grandparents_kind)})
    return second, "第二顺序（兄弟姐妹、祖父母、外祖父母）"


def calculate(a) -> Dict[str, Any]:
    estate = float(a.estate)
    debts = float(a.debts or 0)

    # 第一步：夫妻共同财产先分出配偶一半（第1153条）
    if a.marital == "yes" and a.spouse:
        spouse_prior = estate / 2.0
        residue = estate / 2.0
        marital_note = ("被继承人与配偶无特别约定，按第1153条第1款先将共同财产的 1/2 分出为配偶所有，"
                        "其余 1/2 为遗产。如有书面财产约定，按约定处理。")
    elif a.marital == "yes" and not a.spouse:
        spouse_prior = 0.0
        residue = estate
        marital_note = ("已声明为夫妻共同财产但未输入配偶，无法适用第1153条先分一半的规则。"
                        "此处按全部作为遗产处理，需你核实配偶情况。")
    else:
        spouse_prior = 0.0
        residue = estate
        marital_note = "已声明为被继承人个人财产，不适用第1153条先分一半的规则。"

    # 第二步：清偿债务（第1159、1161条）
    if debts > 0:
        if debts >= residue:
            net = 0.0
            debt_note = (f"债务 {debts:,.2f} 元不低于遗产 {residue:,.2f} 元，可分配遗产为 0。"
                         f"依据第1161条，继承人以所得遗产实际价值为限清偿，超过部分自愿偿还的除外；"
                         f"放弃继承的可不负清偿责任。")
        else:
            net = residue - debts
            debt_note = ("分割遗产应当清偿被继承人依法应当缴纳的税款和债务（第1159条），"
                         "清偿以遗产实际价值为限（第1161条）。")
    else:
        net = residue
        debt_note = "未输入债务，本测算不含债务清偿。如存在债务须按第1159条先行清偿。"

    groups, order_label = build_heir_groups(a)
    n = sum(g["count"] for g in groups)
    if n == 0:
        raise SystemExit("错误：继承人数为 0。请至少输入一名继承人（配偶/子女/父母，"
                         "或在没有第一顺序继承人时输入兄弟姐妹/祖父母外祖父母）。")

    # 第三步：权重法计算份额并归一化（按 part 逐个计算，支持组内细分）
    for g in groups:
        for pt in g["parts"]:
            pt["factor"] = FACTORS[pt["kind"]]
            pt["kind_label"] = FACTORS[pt["kind"]]["label"]
            pt["basis"] = FACTORS[pt["kind"]]["basis"]

    # 第三步：基准份额（各情形均取基准系数，权重法归一化）
    all_parts = [(g, pt) for g in groups for pt in g["parts"]]
    weights_base = [FACTORS[pt["kind"]]["base"] * pt["count"] for (_, pt) in all_parts]
    s_base = sum(weights_base)
    for (g, pt), w in zip(all_parts, weights_base):
        pt["share_base"] = (w / s_base) if s_base > 0 else 0.0
        pt["amount_base"] = net * pt["share_base"]
        pt["per_amount_base"] = (pt["amount_base"] / pt["count"]) if pt["count"] else 0.0
    for g in groups:
        g["share_base"] = sum(pt["share_base"] for pt in g["parts"])
        g["amount_base"] = sum(pt["amount_base"] for pt in g["parts"])

    # 第四步：个体区间 —— 固定其他人为基准系数，仅浮动本人的调整幅度。
    # 为什么这么做：份额是相对的。若让所有人的系数同步上下浮动，相对比例会被
    # 归一化抵消甚至反转（别人的系数变大反而拉低你的份额），呈现出来就是
    # "低值大于高值"，无法阅读。因此区间只在"本人系数浮动、他人不变"这个
    # 假设下计算，语义为：在你适用情形的调整幅度取最保守/最宽松估计时，
    # 你各能拿到多少。
    for (g, pt) in all_parts:
        w_other = sum(FACTORS[o["kind"]]["base"] * o["count"]
                      for (og, o) in all_parts if o is not pt)
        for key in ("low", "high"):
            w_self = FACTORS[pt["kind"]][key] * pt["count"]
            s = w_self + w_other
            pt[f"share_{key}"] = (w_self / s) if s > 0 else 0.0
            pt[f"amount_{key}"] = net * pt[f"share_{key}"]
            pt[f"per_amount_{key}"] = (pt[f"amount_{key}"] / pt["count"]) if pt["count"] else 0.0

    # 必留份校验（第1141条 + 继承编解释一第25条）
    if a.must_keep:
        must_keep = [{
            "level": "存在必留份继承人",
            "advice": ("遗嘱应当为缺乏劳动能力又没有生活来源的继承人保留必要的遗产份额（第1141条）。"
                       "遗嘱未保留的，遗产处理时应当先为该继承人留下必要遗产，剩余部分才可参照遗嘱分配"
                       "（《继承编解释（一）》第25条）。「必要份额」的具体数额由人民法院根据实际情况确定，"
                       "本测算不代替认定。"),
            "law": "《民法典》第1141条；《继承编解释（一）》第25条",
        }]
    else:
        must_keep = [{
            "level": "未提示必留份情形",
            "advice": ("如存在缺乏劳动能力又没有生活来源的继承人（如未成年子女、重度残疾且无收入的成年继承人），"
                       "必须保留必要份额，否则遗嘱相关部分无效。本项由用户自行声明，引擎不做推定。"),
            "law": "《民法典》第1141条",
        }]

    notes = [
        "第1130条对「照顾」「多分」「少分」只作定性规定，**法条未给出任何比例数字**。"
        "本报告中的调整幅度（照顾/多分 1.1~1.3 倍、少分 0.5~0.8 倍）属实务惯例估算，"
        "仅用于呈现分配区间，不代表法院必然采纳。",
        "份额采用权重法计算并归一化，同一顺序内份额之和恒为 100%，可手工复核。"
        "若全部继承人适用同一调整系数，归一化后相对比例与均分一致，这是数学上的必然结果，"
        "不代表调整未生效。",
        "「每人区间」的含义是：假设其他继承人的情形固定不变，仅本人的调整幅度在惯例估算区间内浮动时，"
        "本人可得金额的下限与上限。份额是相对值，若让所有人系数同步浮动，相对比例会被归一化抵消，"
        "所以区间不采用同步浮动的算法。",
        "遗产范围以「死亡时遗留的个人合法财产」为限（第1122条）。人身性质的权利、"
        "依法不得继承的财产不纳入测算。",
        "存在合法有效遗嘱或遗赠扶养协议的，按第1123条优先于法定继承处理；"
        "遗嘱未处分的遗产按第1154条适用法定继承。",
        "继承人之间协商同意的，可以不均分（第1130条第5款）。协商结果与本测算不一致的，以协商为准。",
    ]
    if a.fetus:
        notes.append("已计入胎儿保留份（第1155条）。胎儿娩出时是死体的，保留的份额按照法定继承办理。"
                     "胎儿出生后为活体的，保留份归其所有。")

    verify = [
        "遗产是否确为被继承人个人财产，有无夫妻财产约定或其他共有权人（涉及第1153条）。",
        "债务是否为夫妻共同债务、有无担保等其他责任人（直接影响可分配遗产基数）。",
        "各继承人是否「缺乏劳动能力又没有生活来源」（第1141条必留份的认定前提）。",
        "是否存在代位继承（第1128条）或转继承（第1152条）情形，本测算按用户输入的现有人数计算。",
        "是否存在丧偶儿媳/女婿尽了主要赡养义务而作为第一顺序继承人的情形（第1129条）。",
        "当地不动产、股权、存款等各类财产的评估口径与过户税费。",
    ]

    return {
        "estate": estate, "debts": debts, "marital": a.marital,
        "spouse_prior": spouse_prior, "residue": residue, "net": net,
        "marital_note": marital_note, "debt_note": debt_note,
        "order_label": order_label, "people_total": n, "groups": groups,
        "must_keep": must_keep, "notes": notes, "verify": verify, "laws": LAWS,
    }


def fmt(v: float) -> str:
    return f"{v:,.2f}"


def print_text(r: Dict[str, Any]):
    print("=" * 78)
    print("遗产继承分配测算报告")
    print("=" * 78)
    print(f"遗产总额             {fmt(r['estate'])} 元")
    if r["spouse_prior"]:
        print(f"配偶先分（第1153条） {fmt(r['spouse_prior'])} 元")
        print(f"  说明：{r['marital_note']}")
    print(f"计入遗产部分         {fmt(r['residue'])} 元")
    print(f"减：债务清偿         {fmt(r['debts'])} 元")
    print(f"  说明：{r['debt_note']}")
    print(f"可分配遗产净额       {fmt(r['net'])} 元")
    print()
    print(f"继承顺序：{r['order_label']}   合计 {r['people_total']} 人（份）")
    print()
    print(f"{'继承人':<12}{'人数':>4}{'情形':<22}{'基准份额':>9}{'每人基准(元)':>15}{'每人区间(元)':>24}")
    print("-" * 78)
    for g in r["groups"]:
        for pt in g["parts"]:
            rng = f"{fmt(pt['per_amount_low'])} ~ {fmt(pt['per_amount_high'])}"
            kind = pt["kind_label"].split("（")[0]
            print(f"{g['label']:<12}{pt['count']:>4}{kind:<22}"
                  f"{pt['share_base']*100:>8.2f}%{fmt(pt['per_amount_base']):>15}{rng:>24}")
    print("-" * 78)
    print()
    print("【调整依据】")
    for g in r["groups"]:
        for pt in g["parts"]:
            print(f"  {g['label']}（{pt['count']}人）— {pt['kind_label']}")
            print(f"    {pt['basis']}")
    print()
    print("【必留份校验】")
    for m in r["must_keep"]:
        print(f"  {m['level']}：{m['advice']}")
        print(f"    依据：{m['law']}")
    print()
    print("【说明与局限】")
    for n in r["notes"]:
        print(f"  · {n}")
    print()
    print("【需要你核实的事项】")
    for v in r["verify"]:
        print(f"  · {v}")
    print()
    print("本报告由 AI 依据公开法条测算生成，份额为区间参考值，不构成法律意见。")
    print("=" * 78)


def main():
    ap = argparse.ArgumentParser(
        description="遗产继承分配测算器（民法典继承编）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  均分：python scripts/calculator.py --estate 1200000 --marital yes \\\n"
            "            --spouse 1 --children 2 --parents 2 --debts 100000\n"
            "  组内细分（子女2人中1人尽主要扶养义务、1人有能力不尽义务）：\n"
            "        python scripts/calculator.py --estate 800000 --children 2 \\\n"
            "            --children-spec \"support=1,neglect=1\"\n"))
    ap.add_argument("--estate", type=float, required=True, help="遗产总额（元）")
    ap.add_argument("--marital", choices=["yes", "no"], default="no",
                    help="是否夫妻共同财产（yes 时先分出配偶一半，第1153条）")
    ap.add_argument("--debts", type=float, default=0, help="被继承人依法应缴纳的税款和债务合计（元）")
    ap.add_argument("--spouse", type=int, default=0, help="配偶人数（0 或 1）")
    ap.add_argument("--children", type=int, default=0,
                    help="子女人数（含婚生、非婚生、养子女、有扶养关系的继子女）")
    ap.add_argument("--parents", type=int, default=0,
                    help="父母人数（0、1 或 2，含生父母、养父母、有扶养关系的继父母）")
    ap.add_argument("--fetus", type=int, default=0, help="胎儿数（保留份，第1155条）")
    ap.add_argument("--siblings", type=int, default=0, help="兄弟姐妹人数（无第一顺序继承人时才参与）")
    ap.add_argument("--grandparents", type=int, default=0,
                    help="祖父母外祖父母人数（无第一顺序继承人时才参与）")
    for name in ("spouse", "children", "parents", "siblings", "grandparents"):
        ap.add_argument(f"--{name}-kind", dest=f"{name}_kind", choices=list(FACTORS.keys()),
                        default="normal",
                        help=f"{name} 的整体分配情形（组内细分请用 --{name}-spec）")
        ap.add_argument(f"--{name}-spec", dest=f"{name}_spec", default=None,
                        help=f"{name} 的组内细分，格式 情形=人数[,情形=人数]，"
                             f"如 support=1,neglect=1；剩余人数按 --{name}-kind 处理")
    ap.add_argument("--must-keep", action="store_true",
                    help="声明存在缺乏劳动能力又没有生活来源的继承人（触发必留份校验，第1141条）")
    ap.add_argument("--html", nargs="?", const="inheritance-report.html", default=None,
                    help="输出 HTML 报告到指定路径（默认 inheritance-report.html）")
    a = ap.parse_args()

    if a.spouse > 1:
        ap.error("--spouse 只能是 0 或 1")

    r = calculate(a)
    print_text(r)

    if a.html:
        sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
        from report import render_html, save_html
        save_html(render_html(r), a.html)
        print(f"\nHTML 报告已生成：{a.html}")


if __name__ == "__main__":
    main()
