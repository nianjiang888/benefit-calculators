# -*- coding: utf-8 -*-
"""
抚养费测算引擎
=====================================================
输入：支付方收入、收入类型、需负担子女数、子女年龄、当地生活水平（可选）、特殊情况
输出：结构化 JSON（逐项金额 + 算式 + 法律依据 + 充足性校验 + 待核实项）+ 可打印 HTML 报告

核心依据：
  《民法典》第 1067 条第 1款  父母不履行抚养义务的，未成年子女或不能独立生活的成年子女
                              有要求给付抚养费的权利
  《民法典》第 1085 条        离婚后，子女由一方直接抚养的，另一方应当负担部分或全部抚养费
  《婚姻家庭编解释（一）》第 41 条  不能独立生活的成年子女认定
                        第 42 条  抚养费 = 生活费 + 教育费 + 医疗费
                        第 49 条  有固定收入按月总收入 20%~30%；两个以上可提高，一般不超 50%；
                                  无固定收入按当年总收入或同行业平均收入参照上述比例
                        第 50 条  定期给付，有条件可一次性给付
                        第 51 条  无经济收入或下落不明可用财物折抵
                        第 52 条  可协议一方负担全部（但能力明显不足的不予支持）
                        第 53 条  给付至 18 周岁；16~18 周岁以劳动收入为主要生活来源且能维持
                                  当地一般生活水平的，可停止给付
                        第 58 条  可请求增加抚养费的三种情形

本引擎最核心的设计：**给区间，不单点**。
法条给的是比例区间（20%~30%），不是固定数。任何说"你该付 2371 元"的工具都是装的，
本引擎给出低值/基准/高值三档，并说明每一档对应的理由，让人知道自己在区间里的位置。

第二个设计：**做一次充足性校验**。
算出来的数如果明显低于"当地人均消费支出 ÷ 2"（父母各负担一半），就提示可能不足以维持
当地实际生活水平——这正好对应解释一第 58 条第（一）项，是可以请求增加的法定情形。
这一步是大多数同类工具没有的。

作者：InchStep 寸进产品实验室
"""

import os
import sys
import json
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from report import render_html, save_html
except Exception:
    render_html = None
    save_html = None


# ---------------------------------------------------------------------------
# 比例区间表
# 法条只明定「一个子女 20%~30%」「两个以上可适当提高，一般不超 50%」。
# 两档以上的具体取值来自实务惯例，不是法条明文，报告里必须标注清楚。
# ---------------------------------------------------------------------------
RATIO_TABLE = {
    1: {"low": 0.20, "base": 0.25, "high": 0.30,
        "source": "婚姻家庭编解释（一）第49条明定区间",
        "note": "法条明文区间，最没有争议的一档"},
    2: {"low": 0.30, "base": 0.35, "high": 0.40,
        "source": "实务惯例（第49条「可适当提高」，上限 50%）",
        "note": "法条未明定具体比例，30%~40% 为常见判决区间，不是硬性标准"},
    3: {"low": 0.40, "base": 0.45, "high": 0.50,
        "source": "实务惯例（第49条一般不超 50%）",
        "note": "已贴近 50% 法定上限，超过需要特殊理由"},
}
RATIO_TABLE_4PLUS = {"low": 0.45, "base": 0.475, "high": 0.50,
                     "source": "实务惯例（第49条一般不超 50%）",
                     "note": "50% 是法定天花板，实务中极少突破"}

ADULT_AGE = 18
SELF_SUPPORT_AGE = 16


def _money(x: float) -> float:
    return round(x + 1e-9, 2)


def resolve_monthly_income(inp: Dict[str, Any]) -> Dict[str, Any]:
    """把不同收入类型统一折算成月收入基数。"""
    income_type = inp.get("income_type", "fixed")
    if income_type == "fixed":
        v = float(inp.get("payer_monthly_income") or 0)
        return {
            "monthly_income": v,
            "basis": "有固定收入，直接取月总收入",
            "formula": f"月总收入 = {v:,.2f} 元",
            "basis_law": "婚姻家庭编解释（一）第49条第2款",
            "warn": None,
        }
    if income_type == "annual":
        a = float(inp.get("payer_annual_income") or 0)
        v = a / 12.0
        return {
            "monthly_income": v,
            "basis": "无固定收入，按当年总收入折算月均",
            "formula": f"月均收入 = 当年总收入 {a:,.2f} ÷ 12 = {v:,.2f} 元",
            "basis_law": "婚姻家庭编解释（一）第49条第3款",
            "warn": "当年总收入波动大的行业（销售、自由职业），建议取近三年平均，单看一年容易偏高或偏低",
        }
    if income_type == "industry":
        v = float(inp.get("industry_avg_monthly_income") or 0)
        return {
            "monthly_income": v,
            "basis": "无固定收入且无法举证，参照同行业平均收入",
            "formula": f"月均收入 = 同行业平均 {v:,.2f} 元",
            "basis_law": "婚姻家庭编解释（一）第49条第3款",
            "warn": "同行业平均需要来源（统计局分行业工资、招聘平台公开数据），来源不同差异可能很大",
        }
    raise ValueError(f"未知收入类型: {income_type}")


def months_until_adult(child_age_years: float) -> Dict[str, Any]:
    """计算距 18 周岁的剩余月数。"""
    remain = ADULT_AGE - child_age_years
    if remain <= 0:
        return {"months": 0, "ended": True,
                "note": "子女已满 18 周岁，原则上抚养费给付期限届满"}
    months = int(round(remain * 12))
    note = f"至 18 周岁剩余约 {months} 个月"
    if SELF_SUPPORT_AGE <= child_age_years < ADULT_AGE:
        note += "；已满 16 周岁，若以劳动收入为主要生活来源并能维持当地一般生活水平，可停止给付"
    return {"months": months, "ended": False, "note": note}


def adequacy_check(monthly_base: float, local_monthly_cost: Optional[float]) -> Dict[str, Any]:
    """
    充足性校验：算出金额 vs 当地人均消费支出的一半。
    父母双方各负担一半是一个粗略但有实务意义的参照。
    """
    if not local_monthly_cost or local_monthly_cost <= 0:
        return {
            "available": False,
            "note": "未填写当地月人均消费支出，跳过充足性校验（建议补上，这一步能发现算少了的情况）",
        }
    half = local_monthly_cost / 2.0
    ratio = monthly_base / half if half > 0 else 0
    if ratio < 0.8:
        level, advice = "明显偏低", (
            f"测算值 {monthly_base:,.0f} 元低于「当地月人均消费支出 {local_monthly_cost:,.0f} 元 ÷ 2 = {half:,.0f} 元」，"
            "可能不足以维持当地实际生活水平，符合请求增加的法定情形")
        law = "婚姻家庭编解释（一）第58条第（一）项"
    elif ratio < 1.0:
        level, advice = "略低", (
            f"测算值 {monthly_base:,.0f} 元略低于参照值 {half:,.0f} 元，"
            "差距不大，可结合子女实际开销协商")
        law = "参照 婚姻家庭编解释（一）第58条第（一）项"
    else:
        level, advice = "充足", (
            f"测算值 {monthly_base:,.0f} 元达到或超过参照值 {half:,.0f} 元，"
            "就当地生活水平看是够的")
        law = None
    return {
        "available": True,
        "local_monthly_cost": _money(local_monthly_cost),
        "reference_half": _money(half),
        "ratio": _money(ratio),
        "level": level,
        "advice": advice,
        "law": law,
        "note": "参照值用「当地月人均消费支出 ÷ 2」粗略估算（父母各负担一半），不是法律标准，仅供参考",
    }


def calculate(inp: Dict[str, Any]) -> Dict[str, Any]:
    income = resolve_monthly_income(inp)
    mi = income["monthly_income"]

    children = int(inp.get("children_count") or 1)
    if children < 1:
        children = 1
    rt = RATIO_TABLE.get(children, RATIO_TABLE_4PLUS)

    low = _money(mi * rt["low"])
    base = _money(mi * rt["base"])
    high = _money(mi * rt["high"])

    child_age = float(inp.get("child_age_years") or 0)
    period = months_until_adult(child_age)
    m = period["months"]
    lump_low = _money(low * m)
    lump_base = _money(base * m)
    lump_high = _money(high * m)

    check = adequacy_check(base, inp.get("local_monthly_cost"))

    items = [
        {
            "name": "抚养费月标准（低值）",
            "amount": low,
            "formula": f"{mi:,.2f} × {rt['low']*100:.0f}% = {low:,.2f} 元/月",
            "basis": rt["source"],
        },
        {
            "name": "抚养费月标准（基准）",
            "amount": base,
            "formula": f"{mi:,.2f} × {rt['base']*100:.1f}% = {base:,.2f} 元/月",
            "basis": rt["source"] + "；基准取区间中值",
        },
        {
            "name": "抚养费月标准（高值）",
            "amount": high,
            "formula": f"{mi:,.2f} × {rt['high']*100:.0f}% = {high:,.2f} 元/月",
            "basis": rt["source"],
        },
    ]

    notes: List[str] = [rt["note"]]
    if income.get("warn"):
        notes.append(income["warn"])
    notes.append("月总收入一般指工资、奖金、津贴、补贴等全部收入；有的法院按应发、有的按实发，这一点各地不统一，会影响结果")
    notes.append("解释一第42条：抚养费包含生活费、教育费、医疗费——但超出常规的大额教育、医疗支出，实务中通常另行主张分担（第58条第（二）项）")
    if children >= 2:
        notes.append(f"负担 {children} 名子女时，第49条只说「可适当提高、一般不超 50%」，具体比例没有法条明文，本报告取值属实务惯例")
    if period["ended"]:
        notes.append("子女已满 18 周岁；若尚在校接受高中及其以下学历教育，或丧失/部分丧失劳动能力，仍可能属于「不能独立生活的成年子女」，可继续主张")
        notes.append("认定依据：婚姻家庭编解释（一）第41条")

    verify = [
        "支付方月总收入的构成是否完整（奖金、津贴、兼职是否计入）",
        "当地上一年度城镇/农村居民人均消费支出具体数额（统计部门公布口径）",
        "子女是否有大额固定支出（私立学校、长期治疗、康复训练）",
        "支付方是否存在应当降低比例的特殊负担（再婚生育、本人重大疾病、失业）",
    ]

    return {
        "input": inp,
        "income_basis": income,
        "ratio": {
            "children_count": children,
            "low": rt["low"], "base": rt["base"], "high": rt["high"],
            "source": rt["source"],
        },
        "monthly": {"low": low, "base": base, "high": high},
        "period": period,
        "lump_sum": {
            "low": lump_low, "base": lump_base, "high": lump_high,
            "formula": f"月标准 × 剩余 {m} 个月",
            "note": "一次性给付需「有条件」才支持（第50条）；实务中法院支持一次性给付的比例不高，且常因资金时间价值有所折让，此数仅作上限参考",
        },
        "adequacy_check": check,
        "items": items,
        "notes": notes,
        "verify": verify,
        "laws": [
            {"text": "父母不履行抚养义务的，未成年子女或者不能独立生活的成年子女，有要求父母给付抚养费的权利",
             "cite": "《民法典》第1067条第1款"},
            {"text": "离婚后，子女由一方直接抚养的，另一方应当负担部分或者全部抚养费",
             "cite": "《民法典》第1085条"},
            {"text": "抚养费包括子女生活费、教育费、医疗费等费用",
             "cite": "《婚姻家庭编解释（一）》第42条"},
            {"text": "有固定收入的，抚养费一般可以按其月总收入的百分之二十至三十的比例给付；负担两个以上子女抚养费的，比例可以适当提高，但一般不得超过月总收入的百分之五十",
             "cite": "《婚姻家庭编解释（一）》第49条"},
            {"text": "抚养费应当定期给付，有条件的可以一次性给付",
             "cite": "《婚姻家庭编解释（一）》第50条"},
            {"text": "抚养费的给付期限，一般至子女十八周岁为止",
             "cite": "《婚姻家庭编解释（一）》第53条"},
            {"text": "原定抚养费数额不足以维持当地实际生活水平等三种情形，可请求增加",
             "cite": "《婚姻家庭编解释（一）》第58条"},
        ],
    }


def render_text(r: Dict[str, Any]) -> str:
    lines = []
    lines.append("=" * 68)
    lines.append("抚养费测算结果")
    lines.append("=" * 68)
    lines.append("")
    lines.append("【收入基数】")
    lines.append(f"  {r['income_basis']['formula']}")
    lines.append(f"  依据：{r['income_basis']['basis_law']}")
    lines.append("")
    lines.append(f"【子女数】{r['ratio']['children_count']} 名")
    lines.append(f"  比例区间：{r['ratio']['low']*100:.0f}% ~ {r['ratio']['high']*100:.0f}%")
    lines.append(f"  依据：{r['ratio']['source']}")
    lines.append("")
    lines.append("【月抚养费】")
    for it in r["items"]:
        lines.append(f"  {it['name']}：{it['amount']:,.2f} 元/月")
        lines.append(f"      {it['formula']}")
    lines.append("")
    if not r["period"]["ended"]:
        lines.append("【一次性给付（至18周岁）】")
        lines.append(f"  低值：{r['lump_sum']['low']:,.2f} 元")
        lines.append(f"  基准：{r['lump_sum']['base']:,.2f} 元")
        lines.append(f"  高值：{r['lump_sum']['high']:,.2f} 元")
        lines.append(f"  {r['lump_sum']['formula']}")
        lines.append("")
    lines.append("【给付期限】")
    lines.append(f"  {r['period']['note']}")
    lines.append("")
    if r["adequacy_check"].get("available"):
        c = r["adequacy_check"]
        lines.append("【充足性校验】")
        lines.append(f"  参照值（当地月人均消费支出 ÷ 2）：{c['reference_half']:,.2f} 元")
        lines.append(f"  测算值 / 参照值 = {c['ratio']:.2f}  → {c['level']}")
        lines.append(f"  {c['advice']}")
        if c.get("law"):
            lines.append(f"  依据：{c['law']}")
        lines.append("")
    lines.append("【提示】")
    for n in r["notes"]:
        lines.append(f"  · {n}")
    lines.append("")
    lines.append("【需要你核实】")
    for v in r["verify"]:
        lines.append(f"  · {v}")
    lines.append("")
    lines.append("=" * 68)
    return "\n".join(lines)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="抚养费测算引擎")
    ap.add_argument("--income", type=float, help="支付方月总收入（固定收入）")
    ap.add_argument("--annual-income", type=float, help="支付方当年总收入（无固定收入）")
    ap.add_argument("--industry-income", type=float, help="同行业平均月收入")
    ap.add_argument("--children", type=int, default=1, help="需负担的子女数")
    ap.add_argument("--child-age", type=float, required=True, help="子女当前年龄（周岁）")
    ap.add_argument("--local-cost", type=float, help="当地月人均消费支出（用于充足性校验）")
    ap.add_argument("--json", action="store_true", help="只输出 JSON")
    ap.add_argument("--html", help="输出 HTML 报告路径")
    a = ap.parse_args()

    if a.income:
        income_type = "fixed"
    elif a.annual_income:
        income_type = "annual"
    elif a.industry_income:
        income_type = "industry"
    else:
        ap.error("需提供 --income / --annual-income / --industry-income 之一")

    inp = {
        "income_type": income_type,
        "payer_monthly_income": a.income,
        "payer_annual_income": a.annual_income,
        "industry_avg_monthly_income": a.industry_income,
        "children_count": a.children,
        "child_age_years": a.child_age,
        "local_monthly_cost": a.local_cost,
    }
    r = calculate(inp)

    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(render_text(r))

    if a.html and render_html:
        save_html(render_html(r), a.html)
        print(f"\nHTML 报告已生成：{a.html}")


if __name__ == "__main__":
    main()
