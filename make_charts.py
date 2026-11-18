"""Make PNG images of each chart for use in the Google Doc.

Usage: python3 make_charts.py   (then run the printed Chrome commands, or see the project notes)
Writes charts/*.html wrappers; screenshot them to PNG with headless Chrome.
"""
import os
import re

import build_report as b

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "charts")
os.makedirs(OUT, exist_ok=True)

CSS = """
body{margin:0;background:#fff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#2b2f42}
.box{padding:18px 22px}
h3{margin:0 0 6px;font-size:18px}
svg{width:100%;height:auto;display:block}
table.hm{width:100%;border-collapse:separate;border-spacing:3px;font-size:15px}
table.hm th{font-size:12.5px;text-align:center;color:#5b6075;padding:6px 4px;font-weight:600}
table.hm td{text-align:center;padding:12px 4px;border-radius:7px;font-weight:600}
table.hm td.cn{text-align:left;background:none;font-weight:700}
td.cn span{display:block;font-size:11px;color:#8a8fa3;font-weight:400}
td.tot{background:#2b2f42;color:#fff;font-size:16px}
.legend{display:flex;gap:14px;font-size:12px;color:#6b7088;margin-top:10px;align-items:center}
.grad{height:10px;width:160px;border-radius:5px;background:linear-gradient(90deg,#bfe3c0,#fbe3a1,#e8694a)}
"""

charts = {
    "1_flow": ("How the data fits together", b.flow_diagram(), 980),
    "2_heat_days": ("Average days at or above 100°F per year, 2015–2024", b.bar_chart_heat(), 760),
    "3_neuro_vs_er": ("Neurologist access vs. ER drive time", b.bubble_chart(), 760),
    "4_risk_score": ("Heat-risk and access-gap score by county", b.stacked_chart(), 760),
    "5_heatmap": ("Every measure at a glance (color = rank, higher = more risk)",
                  b.heatmap() + '<div class="legend"><span>lower risk</span><div class="grad"></div><span>higher risk</span></div>', 860),
}

sizes = {}
for name, (title, body, width) in charts.items():
    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', body)
    if m:
        h = int(width * int(m.group(2)) / int(m.group(1))) + 80
    else:
        h = 470
    page = f'<!doctype html><meta charset="utf-8"><style>{CSS}</style><div class="box" style="width:{width-44}px"><h3>{title}</h3>{body}</div>'
    path = os.path.join(OUT, f"{name}.html")
    open(path, "w").write(page)
    sizes[name] = (width, h)
    print(name, width, h)

import json
json.dump(sizes, open(os.path.join(OUT, "sizes.json"), "w"))
