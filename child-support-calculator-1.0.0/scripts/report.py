# -*- coding: utf-8 -*-
"""抚养费测算报告渲染（A4 可打印 HTML）。"""

import html
from typing import Any, Dict


CSS = """
*{box-sizing:border-box}
body{font-family:"Microsoft YaHei","PingFang SC",sans-serif;margin:0;padding:32px;
    color:#1a1a1a;background:#fff;line-height:1.7}
.page{max-width:820px;margin:0 auto}
h1{font-size:24px;margin:0 0 6px;font-weight:700}
.sub{color:#666;font-size:13px;margin-bottom:24px;border-bottom:2px solid #1a1a1a;padding-bottom:14px}
h2{font-size:16px;margin:28px 0 12px;padding-left:10px;border-left:4px solid #1a1a1a}
table{width:100%;border-collapse:collapse;margin:10px 0;font-size:14px}
th,td{border:1px solid #d8d8d8;padding:9px 11px;text-align:left;vertical-align:top}
th{background:#f4f4f4;font-weight:600}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.big{font-size:26px;font-weight:700;color:#b3261e}
.hero{background:#fafafa;border:1px solid #e2e2e2;border-radius:6px;padding:18px 20px;margin:14px 0}
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
    try:
        return f"{float(v):,.2f}"
    except Exception:
        return str(v)


def render_html(r: Dict[str, Any]) -> str:
    ib = r["income_basis"]
    mo = r["monthly"]
    ls = r["lump_sum"]
    ac = r["adequacy_check"]
    p = r["period"]

    parts = []
    parts.append('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">')
    parts.append('<meta name="viewport" content="width=device-width,initial-scale=1">')
    parts.append('<title>抚养费测算报告</title>')
    parts.append(f"<style>{CSS}</style></head><body><div class='page'>")
    parts.append("<h1>抚养费测算报告</h1>")
    parts.append("<div class='sub'>依据《民法典》第1067条、第1085条及《最高人民法院关于适用〈中华人民共和国民法典〉婚姻家庭编的解释（一）》第41、42、49、50、53、58条测算 · 结果仅供参考，不构成法律意见</div>")

    # 结论
    parts.append("<h2>一、测算结论</h2>")
    parts.append("<div class='hero'>")
    parts.append(f"<div class='row'><span>收入基数</span><b>{_e(ib['formula'])}</b></div>")
    parts.append(f"<div class='row'><span>需负担子女</span><b>{r['ratio']['children_count']} 名</b></div>")
    parts.append(f"<div class='row'><span>适用比例区间</span><b>{r['ratio']['low']*100:.0f}% ~ {r['ratio']['high']*100:.0f}%</b></div>")
    parts.append(f"<div class='row hl'><span>月抚养费建议区间</span><span class='big'>{_m(mo['low'])} ~ {_m(mo['high'])} 元</span></div>")
    parts.append(f"<div class='row'><span>其中基准值</span><b>{_m(mo['base'])} 元/月</b></div>")
    parts.append("</div>")
    if not p["ended"]:
        parts.append(f"<div class='note'><b>一次性给付（至18周岁，剩余 {p['months']} 个月）参考：</b>"
                     f"低值 {_m(ls['low'])} 元 / 基准 {_m(ls['base'])} 元 / 高值 {_m(ls['high'])} 元。"
                     f"{_e(ls['note'])}</div>")
    else:
        parts.append(f"<div class='warn'>{_e(p['note'])}</div>")

    # 逐项
    parts.append("<h2>二、逐项金额与算式</h2>")
    parts.append("<table><tr><th>项目</th><th style='width:130px'>金额（元/月）</th><th>算式</th><th style='width:210px'>依据</th></tr>")
    for it in r["items"]:
        parts.append(f"<tr><td>{_e(it['name'])}</td><td class='num'>{_m(it['amount'])}</td>"
                     f"<td>{_e(it['formula'])}</td><td class='law'>{_e(it['basis'])}</td></tr>")
    parts.append("</table>")

    # 充足性
    parts.append("<h2>三、充足性校验</h2>")
    if ac.get("available"):
        cls = "ok" if ac["level"] == "充足" else ("warn" if ac["level"] == "明显偏低" else "note")
        parts.append(f"<table><tr><th style='width:180px'>当地月人均消费支出</th><td class='num'>{_m(ac['local_monthly_cost'])} 元</td></tr>"
                     f"<tr><th>参照值（÷2）</th><td class='num'>{_m(ac['reference_half'])} 元</td></tr>"
                     f"<tr><th>测算值 / 参照值</th><td class='num'>{ac['ratio']:.2f}</td></tr></table>")
        parts.append(f"<div class='{cls}'><b>{_e(ac['level'])}：</b>{_e(ac['advice'])}"
                     + (f"<br><span class='law'>依据：{_e(ac['law'])}</span>" if ac.get("law") else "") + "</div>")
        parts.append(f"<div class='note'>{_e(ac['note'])}</div>")
    else:
        parts.append(f"<div class='note'>{_e(ac['note'])}</div>")

    # 给付期限
    parts.append("<h2>四、给付期限</h2>")
    parts.append(f"<div class='note'>{_e(p['note'])}<br>"
                 "<span class='law'>依据：《婚姻家庭编解释（一）》第53条；成年子女例外见第41条</span></div>")

    # 提示
    parts.append("<h2>五、测算说明与局限</h2><ul>")
    for n in r["notes"]:
        parts.append(f"<li>{_e(n)}</li>")
    parts.append("</ul>")

    # 待核实
    parts.append("<h2>六、需要你核实的事项</h2><ul>")
    for v in r["verify"]:
        parts.append(f"<li>{_e(v)}</li>")
    parts.append("</ul>")

    # 法条
    parts.append("<h2>七、法律依据原文摘录</h2><table>")
    parts.append("<tr><th style='width:230px'>条款</th><th>内容</th></tr>")
    for l in r["laws"]:
        parts.append(f"<tr><td class='law'>{_e(l['cite'])}</td><td>{_e(l['text'])}</td></tr>")
    parts.append("</table>")

    parts.append("<div class='foot'>本报告由 AI 依据公开法条测算生成，金额为区间参考值，"
                 "不构成法律意见。实际数额以双方协议或人民法院判决为准。"
                 "如遇个案争议，建议咨询当地律师或法律援助机构。</div>")
    parts.append("</div></body></html>")
    return "".join(parts)


def save_html(content: str, path: str) -> str:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
