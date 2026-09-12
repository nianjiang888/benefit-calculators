# -*- coding: utf-8 -*-
"""赡养费测算报告渲染（A4 可打印 HTML）。"""

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
td.mid{text-align:center;white-space:nowrap}
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


def render_html(r: Dict[str, Any]) -> str:
    p = []
    p.append('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">')
    p.append('<meta name="viewport" content="width=device-width,initial-scale=1">')
    p.append('<title>赡养费测算报告</title>')
    p.append(f"<style>{CSS}</style></head><body><div class='page'>")
    p.append("<h1>赡养费测算报告</h1>")
    p.append("<div class='sub'>依据《民法典》第26条、第1067条第2款及《老年人权益保障法》"
             "第14、15、19、20条测算 · <b>赡养费不存在法定计算公式，本报告为参照口径下的估算，"
             "不构成法律意见</b></div>")

    # 一、需求
    p.append("<h2>一、月需求与缺口测算</h2><table>")
    p.append("<tr><th style='width:200px'>项目</th><th style='width:150px'>金额（元/月）</th><th>算式与口径</th></tr>")
    for it in r["items"]:
        p.append(f"<tr><td>{_e(it['name'])}</td><td class='num'>{_m(it['amount'])}</td>"
                 f"<td>{_e(it['formula'])}<br><span class='law'>{_e(it['basis'])}</span></td></tr>")
    p.append(f"<tr><th>月缺口（保底档）</th><td class='num'><b>{_m(r['gap_low'])}</b></td>"
             f"<td class='law'>保底档需求 − 老人自有收入，不低于 0</td></tr>")
    p.append(f"<tr><th>月缺口（合理档）</th><td class='num'><b>{_m(r['gap_high'])}</b></td>"
             f"<td class='law'>合理档需求 − 老人自有收入，不低于 0</td></tr>")
    p.append("</table>")

    # 二、分摊
    sh, sl = r["split_high"], r["split_low"]
    p.append("<h2>二、分摊结论</h2>")
    if sh:
        p.append("<div class='hero'>")
        p.append(f"<div class='row'><span>成年子女人数</span><b>{r['children']} 人</b></div>")
        p.append(f"<div class='row'><span>人均摊（保底档）</span><b>{_m(sl['equal']) if sl else '—'} 元/月</b></div>")
        p.append(f"<div class='row'><span>人均摊（合理档）</span><b>{_m(sh['equal'])} 元/月</b></div>")
        p.append(f"<div class='row hl'><span>合理档合计（按能力加权）</span>"
                 f"<span class='big'>{_m(sum(sh['weighted']))} 元/月</span></div>")
        p.append("</div>")
    p.append("<table><tr><th>子女</th><th style='width:120px'>月收入（元）</th>"
             "<th style='width:120px'>均摊·保底档</th><th style='width:120px'>均摊·合理档</th>"
             "<th style='width:150px'>按能力加权·合理档</th></tr>")
    for i, inc in enumerate(r["incomes"], 1):
        p.append(f"<tr><td>第 {i} 位</td><td class='num'>{_m(inc)}</td>"
                 f"<td class='num'>{_m(sl['equal']) if sl else '—'}</td>"
                 f"<td class='num'>{_m(sh['equal']) if sh else '—'}</td>"
                 f"<td class='num'>{_m(sh['weighted'][i-1]) if sh else '—'}</td></tr>")
    p.append("</table>")
    if sh:
        p.append(f"<div class='note'>{_e(sh['weight_note'])}</div>")

    # 三、门槛校验
    p.append("<h2>三、法条门槛校验（第1067条第2款）</h2>")
    cls = "ok" if r["threshold_level"] == "满足给付要件" else (
        "warn" if r["threshold_level"] == "可能未达给付要件" else "note")
    p.append(f"<div class='{cls}'><b>{_e(r['threshold_level'])}：</b>{_e(r['threshold_note'])}</div>")

    # 四、说明
    p.append("<h2>四、测算说明与局限</h2><ul>")
    for n in r["notes"]:
        p.append(f"<li>{_e(n)}</li>")
    p.append("</ul>")

    # 五、核实
    p.append("<h2>五、需要你核实的事项</h2><ul>")
    for v in r["verify"]:
        p.append(f"<li>{_e(v)}</li>")
    p.append("</ul>")

    # 六、法条
    p.append("<h2>六、法律依据原文摘录</h2><table>")
    p.append("<tr><th style='width:200px'>条款</th><th>内容</th></tr>")
    for l in r["laws"]:
        p.append(f"<tr><td class='law'>{_e(l['cite'])}</td><td>{_e(l['text'])}</td></tr>")
    p.append("</table>")

    p.append("<div class='foot'>本报告由 AI 依据公开法条测算生成。赡养费不存在法定计算公式或比例，"
             "本报告输出的是参照口径下的估算区间，不构成法律意见。"
             "实际数额以赡养协议、人民调解协议或人民法院判决为准。"
             "赡养义务包含经济供养、生活照料与精神慰藉三方面，金钱给付只是其中之一。</div>")
    p.append("</div></body></html>")
    return "".join(p)


def save_html(content: str, path: str) -> str:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
