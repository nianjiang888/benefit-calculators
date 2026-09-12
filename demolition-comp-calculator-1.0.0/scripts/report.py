# -*- coding: utf-8 -*-
"""征收拆迁补偿测算报告渲染（A4 可打印 HTML）。"""

import html
from typing import Any, Dict

CSS = """
*{box-sizing:border-box}
body{font-family:"Microsoft YaHei","PingFang SC",sans-serif;margin:0;padding:32px;
    color:#1a1a1a;background:#fff;line-height:1.7}
.page{max-width:860px;margin:0 auto}
h1{font-size:24px;margin:0 0 6px;font-weight:700}
.sub{color:#666;font-size:13px;margin-bottom:24px;border-bottom:2px solid #1a1a1a;padding-bottom:14px}
h2{font-size:16px;margin:28px 0 12px;padding-left:10px;border-left:4px solid #1a1a1a}
table{width:100%;border-collapse:collapse;margin:10px 0;font-size:14px}
th,td{border:1px solid #d8d8d8;padding:9px 11px;text-align:left;vertical-align:top}
th{background:#f4f4f4;font-weight:600}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.big{font-size:24px;font-weight:700;color:#b3261e}
.hero{background:#fafafa;border:1px solid #e2e2e2;border-radius:6px;padding:16px 20px;margin:14px 0}
.hero .row{display:flex;justify-content:space-between;padding:5px 0;font-size:15px}
.hero .row.hl{border-top:1px dashed #ccc;margin-top:8px;padding-top:10px}
.note{background:#fffbe9;border-left:4px solid #e0a800;padding:11px 14px;margin:10px 0;font-size:13px}
.warn{background:#fdf0ef;border-left:4px solid #b3261e;padding:11px 14px;margin:10px 0;font-size:13px}
.ok{background:#eef7ee;border-left:4px solid #2e7d32;padding:11px 14px;margin:10px 0;font-size:13px}
ul{margin:8px 0;padding-left:20px}li{margin:5px 0;font-size:14px}
.law{font-size:12.5px;color:#444}
.foot{margin-top:36px;padding-top:14px;border-top:1px solid #ddd;font-size:12px;color:#777}
@media print{body{padding:0}.page{max-width:none}}
"""


def _e(s: Any) -> str:
    return html.escape(str(s))


def _m(v: Any) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):,.2f}"
    except Exception:
        return str(v)


def _items_table(items):
    rows = ["<table><tr><th>项目</th><th style='width:150px'>金额（元）</th>"
            "<th style='width:180px'>算式</th><th>依据</th></tr>"]
    for i in items:
        rows.append(f"<tr><td>{_e(i['name'])}</td><td class='num'>{_m(i['amount'])}</td>"
                    f"<td>{_e(i['formula'])}</td><td class='law'>{_e(i['basis'])}</td></tr>")
    rows.append("</table>")
    return "".join(rows)


def render_html(r: Dict[str, Any]) -> str:
    p = []
    p.append('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">')
    p.append('<meta name="viewport" content="width=device-width,initial-scale=1">')
    p.append('<title>征收拆迁补偿测算报告</title>')
    p.append(f"<style>{CSS}</style></head><body><div class='page'>")
    p.append("<h1>征收拆迁补偿测算报告</h1>")
    p.append("<div class='sub'>依据《国有土地上房屋征收与补偿条例》（国务院令第590号）"
             "第2、17、18、19、21、22、23、24、27条及《土地管理法》第48条 · "
             "<b>第19条给的是法定下限而非计算公式，本报告为方案对比与下限校验，不构成法律意见</b></div>")

    # 一、基本情况
    p.append("<h2>一、基本情况</h2><table>")
    p.append(f"<tr><th style='width:200px'>合法建筑面积</th><td class='num'>{_m(r['legal_area'])} ㎡</td></tr>")
    if r["illegal_area"]:
        p.append(f"<tr><th>未经登记面积</th><td class='num'>{_m(r['illegal_area'])} ㎡（不计入补偿）</td></tr>")
    p.append(f"<tr><th>计算单价</th><td class='num'>{_m(r['base_price'])} 元/㎡</td></tr>")
    p.append(f"<tr><th>被征收房屋价值</th><td class='num'><b>{_m(r['house_value'])} 元</b></td></tr>")
    p.append("</table>")
    p.append(f"<div class='note'>{_e(r['price_note'])}</div>")

    # 二、下限校验
    p.append("<h2>二、法定下限校验（第19条）</h2>")
    for c in r["checks"]:
        cls = "warn" if c["level"] == "低于法定下限" else ("ok" if c["level"] == "未低于法定下限" else "note")
        p.append(f"<div class='{cls}'><b>{_e(c['level'])}：</b>{_e(c['text'])}"
                 f"<br><span class='law'>依据：{_e(c['law'])}</span></div>")

    # 三、方案A
    p.append("<h2>三、方案 A：货币补偿</h2>")
    p.append(_items_table(r["plan_a_items"]))
    p.append(f"<div class='hero'><div class='row hl'><span>货币补偿合计</span>"
             f"<span class='big'>{_m(r['plan_a_total'])} 元</span></div></div>")

    # 四、方案B
    if r["plan_b"]:
        b = r["plan_b"]
        p.append("<h2>四、方案 B：房屋产权调换</h2>")
        p.append(_items_table(b["items"]))
        p.append(f"<div class='note'><b>差价结清：</b>{_e(b['diff_text'])}"
                 f"<br><span class='law'>依据：第21条第2款——应当计算、结清被征收房屋价值与"
                 f"用于产权调换房屋价值的差价</span></div>")
        p.append(f"<div class='hero'><div class='row'><span>实际可得现金净额</span>"
                 f"<b>{_m(b['net'])} 元</b></div>"
                 f"<div class='row hl'><span>折算总权益（调换房屋价值 + 各项补偿 − 需补差价）</span>"
                 f"<span class='big'>{_m(b['equity'])} 元</span></div></div>")
        # 对比
        d = b["equity"] - r["plan_a_total"]
        verdict = "产权调换总权益更高" if d > 0 else ("货币补偿更高" if d < 0 else "两者相当")
        p.append("<h2>五、方案对比</h2><table>")
        p.append(f"<tr><th style='width:200px'>方案 A 货币补偿（到手现金）</th>"
                 f"<td class='num'>{_m(r['plan_a_total'])} 元</td></tr>")
        p.append(f"<tr><th>方案 B 产权调换（折算总权益）</th><td class='num'>{_m(b['equity'])} 元</td></tr>")
        p.append(f"<tr><th>差额</th><td class='num'>{_m(d)} 元（{verdict}）</td></tr>")
        p.append("</table>")
        p.append("<div class='note'>两者性质不同：货币补偿是确定的现金，产权调换的价值取决于"
                 "调换房屋的区位与市场行情，不可简单以数字大小论优劣。</div>")
    else:
        p.append("<h2>四、方案 B：房屋产权调换</h2>")
        p.append("<div class='note'>未提供产权调换房屋的单价与面积，未做该方案测算。"
                 "依第21条第1款，被征收人有权在货币补偿与房屋产权调换之间选择。</div>")

    # 未经登记建筑
    if r["illegal_note"]:
        p.append("<h2>未经登记建筑提示（第24条）</h2>")
        p.append(f"<div class='warn'>{_e(r['illegal_note'])}</div>")

    # 说明
    p.append("<h2>测算说明与局限</h2><ul>")
    for n in r["notes"]:
        p.append(f"<li>{_e(n)}</li>")
    p.append("</ul>")

    # 核实
    p.append("<h2>需要你核实的事项</h2><ul>")
    for v in r["verify"]:
        p.append(f"<li>{_e(v)}</li>")
    p.append("</ul>")

    # 法条
    p.append("<h2>法律依据原文摘录</h2><table>")
    p.append("<tr><th style='width:230px'>条款</th><th>内容</th></tr>")
    for l in r["laws"]:
        p.append(f"<tr><td class='law'>{_e(l['cite'])}</td><td>{_e(l['text'])}</td></tr>")
    p.append("</table>")

    p.append("<div class='foot'>本报告由 AI 依据公开法条测算生成。第19条规定的是补偿下限而非计算公式，"
             "搬迁费、临时安置费、停产停业损失的具体标准由省级政府制定。"
             "本报告为方案对比与下限校验，不构成法律意见。"
             "实际补偿以评估机构评估结果、补偿协议或补偿决定为准。</div>")
    p.append("</div></body></html>")
    return "".join(p)


def save_html(content: str, path: str) -> str:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
