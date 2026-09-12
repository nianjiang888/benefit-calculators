# -*- coding: utf-8 -*-
"""
征收拆迁补偿测算引擎
======================

国有土地上房屋：依据《国有土地上房屋征收与补偿条例》（国务院令第590号，
2011年1月21日公布施行）第2、17、18、19、21、22、23、24、25、26、27条。
集体土地征收：依据《中华人民共和国土地管理法》（2019年修正）第48条。

**必须先说清楚的三件事：**

1. **第19条给的是下限，不是公式**。条例只规定"对被征收房屋价值的补偿，不得低于
   房屋征收决定公告之日被征收房屋类似房地产的市场价格"，并规定由具有相应资质的
   房地产价格评估机构按房屋征收评估办法评估确定。**不存在全国统一的补偿计算公式**。

2. **搬迁费、临时安置费、停产停业损失的具体标准由省级政府制定**。第23条明文
   "具体办法由省、自治区、直辖市制定"，第22条的标准各地差异极大。本引擎只能
   按你输入的参数计算，不内置任何地区标准。

3. **本引擎的核心价值是「三方案对比 + 法定下限校验」**，不是"算出你该拿多少钱"。
   真正的补偿数额取决于评估机构评估结果与当地征收补偿方案。

用法：
    python scripts/calculator.py --area 90 --market-price 18000 --offer-price 15000 \
        --moving-fee 3000 --temp-monthly 2000 --temp-months 24 --subsidy 50000
    python scripts/calculator.py ... --swap-price 16000 --swap-area 100
    python scripts/calculator.py ... --html report.html
"""

import argparse
import os
import sys
from typing import Any, Dict, List

LAWS = [
    {"cite": "《国有土地上房屋征收与补偿条例》第2条",
     "text": "为了公共利益的需要，征收国有土地上单位、个人的房屋，应当对被征收房屋所有权人"
             "（以下称被征收人）给予公平补偿。"},
    {"cite": "第17条",
     "text": "作出房屋征收决定的市、县级人民政府对被征收人给予的补偿包括：（一）被征收房屋价值的补偿；"
             "（二）因征收房屋造成的搬迁、临时安置的补偿；（三）因征收房屋造成的停产停业损失的补偿。"
             "市、县级人民政府应当制定补助和奖励办法，对被征收人给予补助和奖励。"},
    {"cite": "第19条第1款",
     "text": "对被征收房屋价值的补偿，不得低于房屋征收决定公告之日被征收房屋类似房地产的市场价格。"
             "被征收房屋的价值，由具有相应资质的房地产价格评估机构按照房屋征收评估办法评估确定。"},
    {"cite": "第21条第1、2款",
     "text": "被征收人可以选择货币补偿，也可以选择房屋产权调换。被征收人选择房屋产权调换的，"
             "市、县级人民政府应当提供用于产权调换的房屋，并与被征收人计算、结清被征收房屋价值与"
             "用于产权调换房屋价值的差价。"},
    {"cite": "第22条",
     "text": "因征收房屋造成搬迁的，房屋征收部门应当向被征收人支付搬迁费；选择房屋产权调换的，"
             "产权调换房屋交付前，房屋征收部门应当向被征收人支付临时安置费或者提供周转用房。"},
    {"cite": "第23条",
     "text": "对因征收房屋造成停产停业损失的补偿，根据房屋被征收前的效益、停产停业期限等因素确定。"
             "具体办法由省、自治区、直辖市制定。"},
    {"cite": "第24条第2款",
     "text": "市、县级人民政府作出房屋征收决定前，应当组织有关部门依法对征收范围内未经登记的建筑进行"
             "调查、认定和处理。对认定为合法建筑和未超过批准期限的临时建筑的，应当给予补偿；"
             "对认定为违法建筑和超过批准期限的临时建筑的，不予补偿。"},
    {"cite": "第27条第1、2款",
     "text": "实施房屋征收应当先补偿、后搬迁。作出房屋征收决定的市、县级人民政府对被征收人给予补偿后，"
             "被征收人应当在补偿协议约定或者补偿决定确定的搬迁期限内完成搬迁。"},
    {"cite": "《土地管理法》（2019年修正）第48条第1、2款",
     "text": "征收土地应当给予公平、合理的补偿，保障被征地农民原有生活水平不降低、长远生计有保障。"
             "征收土地应当依法及时足额支付土地补偿费、安置补助费以及农村村民住宅、其他地上附着物和"
             "青苗等的补偿费用，并安排被征地农民的社会保障费用。"},
    {"cite": "《土地管理法》第48条第3款",
     "text": "征收农用地的土地补偿费、安置补助费标准由省、自治区、直辖市通过制定公布区片综合地价确定。"
             "制定区片综合地价应当综合考虑土地原用途、土地资源条件、土地产值、土地区位、土地供求关系、"
             "人口以及经济社会发展水平等因素，并至少每三年调整或者重新公布一次。"},
]


def calculate(a) -> Dict[str, Any]:
    legal_area = float(a.area)                 # 合法建筑面积
    illegal_area = float(a.illegal_area or 0)  # 未经登记/违法建筑面积
    market_price = float(a.market_price or 0)  # 类似房地产市场价格（元/㎡）
    offer_price = float(a.offer_price or 0)    # 征收方提出的补偿单价
    moving_fee = float(a.moving_fee or 0)
    temp_monthly = float(a.temp_monthly or 0)
    temp_months = float(a.temp_months or 0)
    biz_profit = float(a.biz_profit or 0)
    biz_months = float(a.biz_months or 0)
    subsidy = float(a.subsidy or 0)
    swap_price = float(a.swap_price or 0)
    swap_area = float(a.swap_area or 0)

    if legal_area <= 0:
        raise SystemExit("错误：--area（合法建筑面积）必须大于 0")
    if market_price <= 0 and offer_price <= 0:
        raise SystemExit("错误：--market-price 与 --offer-price 至少要填一个")

    # 一、法定下限校验（第19条）
    checks = []
    if offer_price > 0 and market_price > 0:
        base_price = max(offer_price, market_price)
        if offer_price < market_price:
            gap = (market_price - offer_price) * legal_area
            checks.append({
                "level": "低于法定下限",
                "text": (f"征收方提出的单价 {offer_price:,.0f} 元/㎡ 低于类似房地产市场价格 "
                         f"{market_price:,.0f} 元/㎡。依第19条第1款，对被征收房屋价值的补偿"
                         f"**不得低于**征收决定公告之日类似房地产的市场价格。"
                         f"按合法面积 {legal_area:,.0f} ㎡ 计，差额约 {gap:,.0f} 元，"
                         f"这部分属于你可以主张的缺口。"),
                "law": "《国有土地上房屋征收与补偿条例》第19条第1款",
            })
        else:
            checks.append({
                "level": "未低于法定下限",
                "text": (f"征收方提出的单价 {offer_price:,.0f} 元/㎡ 不低于类似房地产市场价格 "
                         f"{market_price:,.0f} 元/㎡，符合第19条第1款的下限要求。"
                         f"注意：这只是**下限**，不是应得数额。"),
                "law": "《国有土地上房屋征收与补偿条例》第19条第1款",
            })
        house_value = base_price * legal_area
        price_note = f"按 {'征收方报价' if offer_price >= market_price else '市场价（法定下限）'} {base_price:,.0f} 元/㎡ 计算"
    else:
        p = offer_price or market_price
        house_value = p * legal_area
        base_price = p
        price_note = f"仅提供了单一价格 {p:,.0f} 元/㎡，无法做下限校验，建议补充另一项"
        checks.append({
            "level": "无法校验",
            "text": "至少需要同时提供「类似房地产市场价格」与「征收方报价」才能做第19条下限校验。",
            "law": "《国有土地上房屋征收与补偿条例》第19条第1款",
        })

    # 二、方案 A：货币补偿（第17、19、22、23条）
    temp_total = temp_monthly * temp_months
    biz_total = biz_profit * biz_months
    plan_a_items = [
        {"name": "被征收房屋价值补偿", "amount": house_value,
         "formula": f"{base_price:,.0f} 元/㎡ × {legal_area:,.0f} ㎡",
         "basis": "第17条第（一）项、第19条（不低于类似房地产市场价格）"},
        {"name": "搬迁费", "amount": moving_fee,
         "formula": "按征收补偿方案 / 协商确定",
         "basis": "第17条第（二）项、第22条（标准由各地规定）"},
        {"name": "临时安置费", "amount": temp_total,
         "formula": f"{temp_monthly:,.0f} 元/月 × {temp_months:,.0f} 月",
         "basis": "第17条第（二）项、第22条（选择货币补偿的是否给付、给付多久，各地口径不一）"},
        {"name": "停产停业损失补偿", "amount": biz_total,
         "formula": f"{biz_profit:,.0f} 元/月 × {biz_months:,.0f} 月",
         "basis": "第17条第（三）项、第23条（具体办法由省级政府制定）"},
        {"name": "补助和奖励", "amount": subsidy,
         "formula": "按市县级政府制定的补助奖励办法",
         "basis": "第17条第2款"},
    ]
    plan_a_total = sum(i["amount"] for i in plan_a_items)

    # 三、方案 B：产权调换（第21、22条）
    plan_b = None
    if swap_price > 0 and swap_area > 0:
        swap_value = swap_price * swap_area
        diff = swap_value - house_value   # 正=被征收人补差，负=征收方结清
        # 产权调换情形下通常发生两次搬迁（搬出 + 搬入），实务常见按两倍计
        moving_b = moving_fee * 2
        plan_b_items = [
            {"name": "被征收房屋价值", "amount": house_value,
             "formula": f"{base_price:,.0f} 元/㎡ × {legal_area:,.0f} ㎡",
             "basis": "第19条（计算差价的基础）"},
            {"name": "产权调换房屋价值", "amount": swap_value,
             "formula": f"{swap_price:,.0f} 元/㎡ × {swap_area:,.0f} ㎡",
             "basis": "第21条第2款（用于产权调换房屋的价值）"},
            {"name": "差价结清", "amount": -diff,
             "formula": f"{house_value:,.0f} − {swap_value:,.0f}",
             "basis": "第21条第2款（应当计算、结清差价）"},
            {"name": "搬迁费（搬出 + 搬入）", "amount": moving_b,
             "formula": f"{moving_fee:,.0f} × 2",
             "basis": "第22条（实务常见按两次计，以当地方案为准）"},
            {"name": "临时安置费（至交付前）", "amount": temp_total,
             "formula": f"{temp_monthly:,.0f} 元/月 × {temp_months:,.0f} 月",
             "basis": "第22条（产权调换房屋交付前应当支付或提供周转用房）"},
            {"name": "停产停业损失补偿", "amount": biz_total,
             "formula": f"{biz_profit:,.0f} 元/月 × {biz_months:,.0f} 月",
             "basis": "第23条"},
            {"name": "补助和奖励", "amount": subsidy,
             "formula": "按市县级政府制定的补助奖励办法",
             "basis": "第17条第2款"},
        ]
        net_b = -diff + moving_b + temp_total + biz_total + subsidy
        plan_b = {
            "items": plan_b_items,
            "swap_value": swap_value,
            "diff": diff,
            "diff_text": (f"需由被征收人补交差价 {diff:,.0f} 元"
                          if diff > 0 else
                          (f"应由征收方向被征收人结清 {abs(diff):,.0f} 元" if diff < 0
                           else "两处价值相当，无需结清差价")),
            "net": net_b,
            "equity": swap_value + moving_b + temp_total + biz_total + subsidy - max(diff, 0),
        }

    # 四、违法建筑提示（第24条）
    illegal_note = ""
    if illegal_area > 0:
        illegal_note = (f"存在未经登记建筑 {illegal_area:,.0f} ㎡。依第24条第2款，市县级政府作出征收决定前"
                        f"应当组织调查、认定和处理：认定为合法建筑和未超过批准期限的临时建筑的，应当给予补偿；"
                        f"认定为违法建筑和超过批准期限的临时建筑的，不予补偿。"
                        f"**本测算未将上述面积计入补偿**，认定结果直接影响最终数额，务必核实。")

    notes = [
        "**第19条给的是下限，不是公式**。条例只规定补偿「不得低于类似房地产的市场价格」，"
        "具体价值由具有相应资质的房地产价格评估机构按房屋征收评估办法评估确定。"
        "不存在全国统一的补偿计算公式。",
        "**搬迁费、临时安置费、停产停业损失的标准由省级政府制定**（第22、23条）。"
        "本引擎按你输入的参数计算，不内置任何地区标准，实际数额以当地征收补偿方案为准。",
        "本引擎的核心价值是**三方案对比与法定下限校验**，不是「算出你该拿多少钱」。"
        "真正的补偿数额取决于评估结果与当地方案。",
        "对评估确定的房屋价值有异议的，可以向房地产价格评估机构申请复核评估；"
        "对复核结果有异议的，可以向房地产价格评估专家委员会申请鉴定（第19条第2款）。",
        "实施房屋征收应当**先补偿、后搬迁**（第27条第1款）。"
        "达不成补偿协议的，由征收部门报请作出补偿决定（第26条），"
        "对补偿决定不服可申请行政复议或提起行政诉讼。",
    ]
    if a.land_type == "collective":
        notes.append("已选择集体土地征收。集体土地适用《土地管理法》第48条而非590号令："
                     "补偿包括土地补偿费、安置补助费（按省级公布的区片综合地价，至少每三年调整一次）、"
                     "农村村民住宅、其他地上附着物和青苗补偿，并安排被征地农民社会保障费用；"
                     "农村村民住宅应当**先补偿后搬迁、居住条件有改善**。"
                     "本引擎对集体土地只做结构提示，未做分项测算。")

    verify = [
        "房屋建筑面积的认定（证载面积 vs 实测面积）与未经登记建筑的认定结果。",
        "「类似房地产市场价格」的取值来源（建议参照征收决定公告之日周边同类房屋成交价或评估价）。",
        "当地最新的征收补偿方案（搬迁费、临时安置费、停产停业损失的具体标准）。",
        "评估机构的资质与评估时点（应为房屋征收决定公告之日）。",
        "经营性用房的认定与效益证明（营业执照、纳税记录、近三年利润）。",
        "过渡期限的约定与超期过渡的违约责任。",
        "产权调换房屋的区位、面积、交付时间与质量标准。",
    ]

    return {
        "legal_area": legal_area, "illegal_area": illegal_area,
        "market_price": market_price, "offer_price": offer_price,
        "base_price": base_price, "house_value": house_value, "price_note": price_note,
        "plan_a_items": plan_a_items, "plan_a_total": plan_a_total,
        "plan_b": plan_b, "checks": checks, "illegal_note": illegal_note,
        "notes": notes, "verify": verify, "laws": LAWS,
        "land_type": a.land_type,
    }


def fmt(v) -> str:
    if v is None:
        return "—"
    return f"{float(v):,.2f}"


def print_text(r: Dict[str, Any]):
    print("=" * 78)
    print("征收拆迁补偿测算报告")
    print("=" * 78)
    print(f"合法建筑面积      {fmt(r['legal_area'])} ㎡")
    if r["illegal_area"]:
        print(f"未经登记面积      {fmt(r['illegal_area'])} ㎡（不计入补偿，见下方提示）")
    print(f"房屋价值计算单价  {fmt(r['base_price'])} 元/㎡   {r['price_note']}")
    print(f"被征收房屋价值    {fmt(r['house_value'])} 元")
    print()
    print("【一、法定下限校验（第19条）】")
    for c in r["checks"]:
        print(f"  {c['level']}：{c['text']}")
        print(f"    依据：{c['law']}")
    print()
    print("【二、方案 A：货币补偿】")
    for i in r["plan_a_items"]:
        print(f"  {i['name']:<22}{fmt(i['amount']):>16} 元   {i['formula']}")
    print(f"  {'合计':<22}{fmt(r['plan_a_total']):>16} 元")
    print()
    if r["plan_b"]:
        b = r["plan_b"]
        print("【三、方案 B：房屋产权调换】")
        for i in b["items"]:
            print(f"  {i['name']:<22}{fmt(i['amount']):>16} 元   {i['formula']}")
        print(f"  差价结清：{b['diff_text']}")
        print(f"  实际可得现金净额：{fmt(b['net'])} 元")
        print(f"  折算总权益（调换房屋价值 + 各项补偿 − 需补差价）：{fmt(b['equity'])} 元")
        print()
        print("【四、方案对比】")
        print(f"  货币补偿到手现金：{fmt(r['plan_a_total'])} 元")
        print(f"  产权调换总权益：  {fmt(b['equity'])} 元")
        d = b["equity"] - r["plan_a_total"]
        print(f"  差额：{fmt(d)} 元（{'产权调换更有利' if d > 0 else '货币补偿更有利' if d < 0 else '两者相当'}）")
        print("  注意：两者性质不同——货币补偿是确定的现金，产权调换的价值取决于调换房屋的区位与市场行情，")
        print("        不可简单以数字大小论优劣。")
    else:
        print("【三、方案 B：房屋产权调换】")
        print("  未提供 --swap-price 与 --swap-area，未做产权调换测算。")
        print("  依第21条，被征收人有权在货币补偿与房屋产权调换之间选择。")
    if r["illegal_note"]:
        print()
        print("【未经登记建筑提示（第24条）】")
        print(f"  {r['illegal_note']}")
    print()
    print("【说明与局限】")
    for n in r["notes"]:
        print(f"  · {n}")
    print()
    print("【需要你核实的事项】")
    for v in r["verify"]:
        print(f"  · {v}")
    print()
    print("本报告由 AI 依据公开法条测算生成，为方案对比与下限校验，不构成法律意见。")
    print("=" * 78)


def main():
    ap = argparse.ArgumentParser(
        description="征收拆迁补偿测算器（国务院令第590号 / 土地管理法第48条）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "注意：第19条给的是法定下限，不是补偿公式。本引擎做三方案对比与下限校验。\n\n"
            "示例：\n"
            "  python scripts/calculator.py --area 90 --market-price 18000 --offer-price 15000 \\\n"
            "      --moving-fee 3000 --temp-monthly 2000 --temp-months 24 --subsidy 50000\n"
            "  加产权调换：\n"
            "      ... --swap-price 16000 --swap-area 100\n"))
    ap.add_argument("--area", type=float, required=True, help="合法建筑面积（㎡）")
    ap.add_argument("--illegal-area", type=float, default=0, help="未经登记/涉嫌违法建筑面积（㎡），不计入补偿")
    ap.add_argument("--market-price", type=float, default=None, help="类似房地产市场价格（元/㎡）")
    ap.add_argument("--offer-price", type=float, default=None, help="征收方提出的补偿单价（元/㎡）")
    ap.add_argument("--moving-fee", type=float, default=0, help="搬迁费（元）")
    ap.add_argument("--temp-monthly", type=float, default=0, help="临时安置费（元/月）")
    ap.add_argument("--temp-months", type=float, default=0, help="过渡期限（月）")
    ap.add_argument("--biz-profit", type=float, default=0, help="停产停业前月净利润（元/月，经营性用房）")
    ap.add_argument("--biz-months", type=float, default=0, help="停产停业期限（月）")
    ap.add_argument("--subsidy", type=float, default=0, help="补助和奖励（元）")
    ap.add_argument("--swap-price", type=float, default=None, help="产权调换房屋单价（元/㎡）")
    ap.add_argument("--swap-area", type=float, default=None, help="产权调换房屋面积（㎡）")
    ap.add_argument("--land-type", choices=["state", "collective"], default="state",
                    help="土地类型：state 国有土地上房屋 / collective 集体土地征收")
    ap.add_argument("--html", nargs="?", const="demolition-report.html", default=None,
                    help="输出 HTML 报告到指定路径（默认 demolition-report.html）")
    a = ap.parse_args()
    if (a.swap_price is None) != (a.swap_area is None):
        ap.error("--swap-price 与 --swap-area 必须同时提供")

    r = calculate(a)
    print_text(r)

    if a.html:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from report import render_html, save_html
        save_html(render_html(r), a.html)
        print(f"\nHTML 报告已生成：{a.html}")


if __name__ == "__main__":
    main()
