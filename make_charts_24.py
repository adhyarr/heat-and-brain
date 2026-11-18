"""Make PNG images of the 24-county charts for the final Google Doc."""
import os, re
import build_report_expanded as b

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "charts_24")
os.makedirs(OUT, exist_ok=True)

CSS = """
body{margin:0;background:#fff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#2b2f42}
.box{padding:16px 20px}
h3{margin:0 0 6px;font-size:17px}
svg{width:100%;height:auto;display:block}
table.hm{width:100%;border-collapse:separate;border-spacing:2.5px;font-size:12.5px}
table.hm th{font-size:11px;text-align:center;color:#5b6075;padding:5px 3px;font-weight:600}
table.hm td{text-align:center;padding:7px 4px;border-radius:5px;font-weight:600}
table.hm td.cn{text-align:left;background:none;font-weight:700}
td.cn span{display:inline-block;margin-left:6px;font-size:10.5px;color:#8a8fa3;font-weight:400}
td.tot{background:#2b2f42;color:#fff;font-size:13px}
.legend{display:flex;gap:14px;font-size:12px;color:#6b7088;margin-top:10px;align-items:center}
.grad{height:10px;width:160px;border-radius:5px;background:linear-gradient(90deg,#bfe3c0,#fbe3a1,#e8694a)}
"""

charts = {
    "fig1_heat": ("Extreme heat days per year (2015–2024, 24 counties)", b.bar_chart_heat(), 760, None),
    "fig2_access": ("Population-weighted ER drive vs. neurology hub drive", b.scatter_access(), 760, None),
    "fig3_scores": ("Combined risk score across 24 counties", b.stacked_chart(), 760, None),
    "fig4_heatmap": ("All 24 counties at a glance (color = rank, higher = more risk)",
                     b.heatmap() + '<div class="legend"><span>lower risk</span><div class="grad"></div><span>higher risk</span></div>', 880, 960),
}

for name, (title, body, width, fixed_h) in charts.items():
    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', body)
    h = fixed_h if fixed_h else int(width * int(m.group(2)) / int(m.group(1))) + 70
    page = f'<!doctype html><meta charset="utf-8"><style>{CSS}</style><div class="box" style="width:{width-40}px"><h3>{title}</h3>{body}</div>'
    open(os.path.join(OUT, f"{name}.html"), "w").write(page)
    print(name, width, h)
