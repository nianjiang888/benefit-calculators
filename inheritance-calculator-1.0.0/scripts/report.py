# -*- coding: utf-8 -*-
"""遗产继承分配测算报告渲染（A4 可打印 HTML）。"""

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
    try:
        return f"{float(v):,.2f}"
    except Exception:
        return str(v)


def render_html(r: Dict[str, Any]) -> str:
    p = []
    p.append('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">')
    p.append('<meta name="viewport" content="width=device-width,initial-scale=1">')
    p.append('<title>遗产继承分配测算报告</title>')
    p.append(f"<style>{CSS}</style></head><body><div class='page'>")
    p.append("<h1>遗产继承分配测算报告</h1>")
    p.append("<div class='sub'>依据《中华人民共和国民法典》继承编第1122、1123、1127、1128、1130、"
             "1141、1153、1155、1159、1161条及《继承编解释（一）》第14、25条测算 · "
             "结果为区间参考值，不构成法律意见</div>")

    # 一、基数
    p.append("<h2>一、可分配遗产基数</h2>")
    p.append("<table>")
    p.append(f"<tr><th style='width:200px'>遗产总额</th><td class='num'>{_m(r['estate'])} 元</td></tr>")
    if r["spouse_prior"]:
        p.append(f"<tr><th>配偶先分（第1153条）</th><td class='num'>{_m(r['spouse_prior'])} 元</td></tr>")
    p.append(f"<tr><th>计入遗产部分</th><td class='num'>{_m(r['residue'])} 元</td></tr>")
    p.append(f"<tr><th>减：债务清偿</th><td class='num'>{_m(r['debts'])} 元</td></tr>")
    p.append(f"<tr><th>可分配遗产净额</th><td class='num'><b>{_m(r['net'])} 元</b></td></tr>")
    p.append("</table>")
    p.append(f"<div class='note'>{_e(r['marital_note'])}</div>")
    p.append(f"<div class='note'>{_e(r['debt_note'])}</div>")

    # 二、结论
    p.append("<h2>二、分配结论</h2>")
    p.append(f"<div class='hero'><div class='row'><span>适用继承顺序</span>"
             f"<b>{_e(r['order_label'])}</b></div>"
             f"<div class='row'><span>继承人数（份）</span><b>{r['people_total']} 人</b></div>"
             f"<div class='row hl'><span>可分配净额</span>"
             f"<span class='big'>{_m(r['net'])} 元</span></div></div>")
    p.append("<table><tr><th>继承人</th><th class='mid'>人数</th><th>适用情形</th>"
             "<th class='mid'>基准份额</th><th style='width:130px'>每人基准（元）</th>"
             "<th style='width:190px'>每人区间（元）</th></tr>")
    for g in r["groups"]:
        for pt in g["parts"]:
            p.append(f"<tr><td>{_e(g['label'])}</td><td class='mid'>{pt['count']}</td>"
                     f"<td class='law'>{_e(pt['kind_label'])}</td>"
                     f"<td class='mid'>{pt['share_base']*100:.2f}%</td>"
                     f"<td class='num'>{_m(pt['per_amount_base'])}</td>"
                     f"<td class='num'>{_m(pt['per_amount_low'])} ~ {_m(pt['per_amount_high'])}</td></tr>")
    p.append("</table>")
    p.append("<div class='note'>份额采用权重法计算并归一化，同一顺序内份额之和恒为 100%，"
             "可手工复核。区间反映第1130条各款调整幅度的不确定性。若全部继承人适用同一系数，"
             "归一化后相对比例与均分一致，属数学必然，不代表调整未生效。</div>")

    # 三、调整依据
    p.append("<h2>三、份额调整依据</h2><table>")
    p.append("<tr><th style='width:130px'>类别</th><th class='mid'>人数</th>"
             "<th style='width:100px'>倍数区间</th><th>依据（法条明文 / 惯例估算）</th></tr>")
    for g in r["groups"]:
        for pt in g["parts"]:
            f = pt["factor"]
            rng = (f"{f['low']:.1f} ~ {f['high']:.1f} 倍" if f["low"] != f["high"] else "1.0 倍（不调整）")
            p.append(f"<tr><td>{_e(g['label'])}</td><td class='mid'>{pt['count']}</td>"
                     f"<td class='mid'>{_e(rng)}</td><td class='law'>{_e(pt['basis'])}</td></tr>")
    p.append("</table>")

    # 四、必留份
    p.append("<h2>四、必留份校验</h2>")
    for m in r["must_keep"]:
        cls = "warn" if m["level"].startswith("存在") else "ok"
        p.append(f"<div class='{cls}'><b>{_e(m['level'])}：</b>{_e(m['advice'])}"
                 f"<br><span class='law'>依据：{_e(m['law'])}</span></div>")

    # 五、说明
    p.append("<h2>五、测算说明与局限</h2><ul>")
    for n in r["notes"]:
        p.append(f"<li>{_e(n)}</li>")
    p.append("</ul>")

    # 六、核实
    p.append("<h2>六、需要你核实的事项</h2><ul>")
    for v in r["verify"]:
        p.append(f"<li>{_e(v)}</li>")
    p.append("</ul>")

    # 七、法条
    p.append("<h2>七、法律依据原文摘录</h2><table>")
    p.append("<tr><th style='width:200px'>条款</th><th>内容</th></tr>")
    for l in r["laws"]:
        p.append(f"<tr><td class='law'>{_e(l['cite'])}</td><td>{_e(l['text'])}</td></tr>")
    p.append("</table>")

    p.append("<div class='foot'>本报告由 AI 依据公开法条测算生成，份额为区间参考值，"
             "不构成法律意见。实际份额以继承人协商结果、人民调解协议或人民法院判决为准。"
             "如存在遗嘱、遗赠扶养协议或跨境财产，建议咨询专业律师。</div>")
    p.append("</div></body></html>")
    return "".join(p)


def save_html(content: str, path: str) -> str:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
