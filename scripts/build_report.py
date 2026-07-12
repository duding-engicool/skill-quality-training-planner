# -*- coding: utf-8 -*-
"""
质量培训策划技能 —— 报告生成器
将结构化培训方案 JSON 渲染为:
  - Markdown 版培训方案
  - 精美网页版 HTML (含课程大纲学时时间轴 SVG + 柯氏四级评估四层卡)

用法:
  python build_report.py --input plan.json --md-out plan.md --html-out plan.html
"""
import argparse
import json
import html
import sys


PRIMARY = "#C8102E"
INK = "#1F2937"
MUTE = "#6B7280"
CARD_BG = "#F9FAFB"
BAR = "#C8102E"
BAR_ALT = "#E8743B"

KIRK_NAMES = {
    "reaction": "反应层（Reaction）",
    "learning": "学习层（Learning）",
    "behavior": "行为层（Behavior）",
    "results": "结果层（Results）",
}


def esc(s):
    return html.escape(str(s), quote=True)


def get(d, *keys, default=""):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k, default)
    return cur if cur is not None else default


def to_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Markdown 渲染
# ---------------------------------------------------------------------------
def build_md(data):
    meta = get(data, "meta", default={})
    lines = []
    lines.append(f"# 质量培训策划方案：{esc(get(meta, 'name', default='未命名培训'))}\n")

    # 元信息
    rows = [
        ("用途场景", get(meta, "scene")),
        ("培训对象", get(meta, "audience")),
        ("培训主题", get(meta, "topic")),
        ("培训时长", get(meta, "duration")),
        ("培训目标", get(meta, "goal")),
        ("特殊要求", get(meta, "special")),
    ]
    lines.append("## 封面与元信息\n")
    for k, v in rows:
        if v:
            lines.append(f"- **{k}**：{esc(v)}")
    lines.append("")

    # 背景
    bg = get(data, "background")
    if bg:
        lines.append("## 一、培训背景与目的\n")
        lines.append(esc(bg) + "\n")

    # 目标
    obj = get(data, "objectives", default={})
    if obj:
        lines.append("## 二、培训目标\n")
        for layer, label in (("knowledge", "知识目标"), ("skill", "技能目标"), ("attitude", "态度目标")):
            items = obj.get(layer, [])
            if items:
                lines.append(f"**{label}：**")
                for it in items:
                    lines.append(f"- {esc(it)}")
        lines.append("")

    # 课程大纲
    mods = get(data, "modules", default=[])
    if mods:
        lines.append("## 三、课程大纲\n")
        for i, m in enumerate(mods, 1):
            period = get(m, "period")
            day = get(m, "day")
            prefix = ""
            if day:
                prefix += f"【{esc(day)}】"
            if period:
                prefix += f"【{esc(period)}】"
            lines.append(f"### 模块{i}：{prefix}{esc(get(m, 'name'))}（{get(m, 'hours')}小时）")
            content = get(m, "content", default=[])
            if content:
                lines.append("**内容要点**：")
                for c in content:
                    lines.append(f"- {esc(c)}")
            method = get(m, "method")
            if method:
                lines.append(f"- 教学方法：{esc(method)}")
            lines.append("")

    # 教学方法设计
    td = get(data, "teaching_design")
    if td:
        lines.append("## 四、教学方法设计\n")
        lines.append(esc(td) + "\n")

    # 考核
    asm = get(data, "assessment", default={})
    if asm:
        lines.append("## 五、考核方式\n")
        for k, label in (("written", "笔试"), ("practical", "实操"), ("project", "项目报告")):
            v = asm.get(k)
            if v:
                lines.append(f"- **{label}**：{esc(v)}")
        lines.append("")

    # 讲师
    tr = get(data, "trainer", default={})
    if tr:
        lines.append("## 六、讲师要求\n")
        for k, label in (("years", "经验年限"), ("expertise", "专业能力"), ("training_exp", "培训经验")):
            v = tr.get(k)
            if v:
                lines.append(f"- {label}：{esc(v)}")
        lines.append("")

    # 资源
    res = get(data, "resources", default={})
    if res:
        lines.append("## 七、资源准备清单\n")
        for k, label in (("equipment", "教具设备"), ("materials", "资料准备"), ("software", "软件工具"), ("venue", "场地要求")):
            v = res.get(k)
            if isinstance(v, list):
                if v:
                    lines.append(f"**{label}**：")
                    for x in v:
                        lines.append(f"- {esc(x)}")
            elif v:
                lines.append(f"- **{label}**：{esc(v)}")
        lines.append("")

    # 柯氏
    kk = get(data, "kirkpatrick", default={})
    if kk:
        lines.append("## 八、效果评估建议（柯氏四级）\n")
        for k, label in KIRK_NAMES.items():
            v = kk.get(k)
            if v:
                lines.append(f"- **{label}**：{esc(v)}")
        lines.append("")

    # 待企业补充
    todo = get(data, "todo", default=[])
    if todo:
        lines.append("## 九、待企业补充项\n")
        for t in todo:
            lines.append(f"- 【待企业补充】{esc(t)}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTML 渲染
# ---------------------------------------------------------------------------
def outline_svg(mods):
    if not mods:
        return ""
    total = sum(to_float(get(m, "hours")) for m in mods)
    if total <= 0:
        total = 1.0
    W = 720
    row_h = 30
    label_w = 200
    bar_max = W - label_w - 80
    H = 30 + len(mods) * (row_h + 6)

    parts = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px;font-family:inherit">']
    for i, m in enumerate(mods):
        y = 24 + i * (row_h + 6)
        name = f"{esc(get(m,'name'))}"
        hrs = to_float(get(m, "hours"))
        bw = max(6, int(hrs / total * bar_max))
        color = BAR if i % 2 == 0 else BAR_ALT
        parts.append(f'<text x="0" y="{y+row_h/2+4}" font-size="12" fill="{INK}">{name}</text>')
        parts.append(f'<rect x="{label_w}" y="{y+4}" width="{bw}" height="{row_h-8}" rx="4" fill="{color}" opacity="0.9"/>')
        parts.append(f'<text x="{label_w+bw+6}" y="{y+row_h/2+4}" font-size="12" fill="{MUTE}">{hrs}h</text>')
    parts.append('</svg>')
    return "\n".join(parts)


def kirk_cards(kk):
    if not kk:
        return ""
    cards = []
    for k, label in KIRK_NAMES.items():
        v = kk.get(k)
        if not v:
            continue
        cards.append(f'''
        <div class="kirk-card">
          <div class="kirk-title">{label}</div>
          <div class="kirk-body">{esc(v)}</div>
        </div>''')
    if not cards:
        return ""
    return f'<div class="kirk-grid">{"".join(cards)}</div>'


def obj_block(obj):
    out = []
    for layer, label in (("knowledge", "知识目标"), ("skill", "技能目标"), ("attitude", "态度目标")):
        items = obj.get(layer, []) if isinstance(obj, dict) else []
        if items:
            lis = "".join(f"<li>{esc(x)}</li>" for x in items)
            out.append(f'<div class="obj-col"><div class="obj-h">{label}</div><ul>{lis}</ul></div>')
    return f'<div class="obj-row">{"".join(out)}</div>' if out else ""


def module_html(mods):
    rows = []
    for i, m in enumerate(mods, 1):
        day = get(m, "day")
        period = get(m, "period")
        tag = " ".join(f'<span class="tag">{esc(t)}</span>' for t in [day, period] if t)
        content = get(m, "content", default=[])
        clis = "".join(f"<li>{esc(c)}</li>" for c in content) if content else ""
        method = get(m, "method")
        rows.append(f'''
        <div class="mod">
          <div class="mod-head">
            <span class="mod-no">模块{i}</span>
            <span class="mod-name">{esc(get(m,'name'))}</span>
            {tag}
            <span class="mod-hrs">{get(m,'hours')}h</span>
          </div>
          {f'<ul class="mod-cl">{clis}</ul>' if clis else ''}
          {f'<div class="mod-method">教学方法：{esc(method)}</div>' if method else ''}
        </div>''')
    return "\n".join(rows)


def build_html(data):
    meta = get(data, "meta", default={})
    name = get(meta, "name", default="未命名培训")
    title = f"质量培训策划方案 · {name}"

    meta_rows = "".join(
        f"<tr><th>{k}</th><td>{esc(v)}</td></tr>"
        for k, v in [
            ("用途场景", get(meta, "scene")),
            ("培训对象", get(meta, "audience")),
            ("培训主题", get(meta, "topic")),
            ("培训时长", get(meta, "duration")),
            ("培训目标", get(meta, "goal")),
            ("特殊要求", get(meta, "special")),
        ]
        if v
    )

    bg = get(data, "background")
    bg_html = f'<section><h2>一、培训背景与目的</h2><p>{esc(bg)}</p></section>' if bg else ""

    obj_html = obj_block(get(data, "objectives", default={}))
    obj_section = f'<section><h2>二、培训目标</h2>{obj_html}</section>' if obj_html else ""

    mods = get(data, "modules", default=[])
    svg = outline_svg(mods)
    mod_html = module_html(mods)
    outline_section = ""
    if mods:
        outline_section = f'''<section>
      <h2>三、课程大纲</h2>
      <div class="svg-box">{svg}</div>
      <div class="mod-list">{mod_html}</div>
    </section>'''

    td = get(data, "teaching_design")
    td_section = f'<section><h2>四、教学方法设计</h2><p>{esc(td)}</p></section>' if td else ""

    asm = get(data, "assessment", default={})
    asm_rows = "".join(
        f"<tr><th>{label}</th><td>{esc(v)}</td></tr>"
        for k, label in (("written", "笔试"), ("practical", "实操"), ("project", "项目报告"))
        if (v := asm.get(k))
    )
    asm_section = f'<section><h2>五、考核方式</h2><table class="kv">{asm_rows}</table></section>' if asm_rows else ""

    tr = get(data, "trainer", default={})
    tr_rows = "".join(
        f"<tr><th>{label}</th><td>{esc(v)}</td></tr>"
        for k, label in (("years", "经验年限"), ("expertise", "专业能力"), ("training_exp", "培训经验"))
        if (v := tr.get(k))
    )
    tr_section = f'<section><h2>六、讲师要求</h2><table class="kv">{tr_rows}</table></section>' if tr_rows else ""

    res = get(data, "resources", default={})
    res_parts = []
    for k, label in (("equipment", "教具设备"), ("materials", "资料准备"), ("software", "软件工具")):
        v = res.get(k)
        if isinstance(v, list) and v:
            lis = "".join(f"<li>{esc(x)}</li>" for x in v)
            res_parts.append(f"<div><b>{label}：</b><ul>{lis}</ul></div>")
    venue = res.get("venue")
    if venue:
        res_parts.append(f"<div><b>场地要求：</b>{esc(venue)}</div>")
    res_section = f'<section><h2>七、资源准备清单</h2><div class="res-grid">{"".join(res_parts)}</div></section>' if res_parts else ""

    kk = get(data, "kirkpatrick", default={})
    kirk_html = kirk_cards(kk)
    kirk_section = f'<section><h2>八、效果评估建议（柯氏四级）</h2>{kirk_html}</section>' if kirk_html else ""

    todo = get(data, "todo", default=[])
    todo_html = ""
    if todo:
        lis = "".join(f"<li>{esc(t)}</li>" for t in todo)
        todo_html = f'<section class="todo"><h2>九、待企业补充项</h2><ul class="todo-list">{lis}</ul></section>'

    return f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>
  :root{{--p:{PRIMARY};--ink:{INK};--mute:{MUTE};--card:{CARD_BG};}}
  *{{box-sizing:border-box;}}
  body{{margin:0;font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;color:var(--ink);background:#fff;line-height:1.7;}}
  .wrap{{max-width:880px;margin:0 auto;padding:32px 24px 64px;}}
  .cover{{border-left:6px solid var(--p);padding:8px 0 8px 18px;margin-bottom:8px;}}
  .cover h1{{font-size:24px;margin:0 0 4px;}}
  .cover .sub{{color:var(--mute);font-size:14px;}}
  table.kv{{width:100%;border-collapse:collapse;margin:10px 0;}}
  table.kv th,table.kv td{{border:1px solid #E5E7EB;padding:8px 12px;text-align:left;vertical-align:top;font-size:14px;}}
  table.kv th{{background:var(--card);width:120px;color:var(--mute);font-weight:600;}}
  section{{margin:28px 0;}}
  h2{{font-size:18px;border-bottom:2px solid var(--p);padding-bottom:6px;}}
  .svg-box{{background:var(--card);border-radius:10px;padding:14px;margin:8px 0;}}
  .mod-list{{margin-top:12px;}}
  .mod{{border:1px solid #E5E7EB;border-radius:10px;padding:12px 14px;margin-bottom:10px;}}
  .mod-head{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}}
  .mod-no{{background:var(--p);color:#fff;font-size:12px;padding:2px 8px;border-radius:6px;}}
  .mod-name{{font-weight:700;font-size:15px;}}
  .tag{{background:#FDECEF;color:var(--p);font-size:12px;padding:2px 8px;border-radius:6px;}}
  .mod-hrs{{margin-left:auto;color:var(--mute);font-size:13px;}}
  .mod-cl{{margin:8px 0 0;padding-left:20px;font-size:14px;}}
  .mod-method{{margin-top:6px;font-size:13px;color:var(--mute);}}
  .obj-row{{display:flex;gap:12px;flex-wrap:wrap;}}
  .obj-col{{flex:1;min-width:200px;background:var(--card);border-radius:10px;padding:12px 14px;}}
  .obj-h{{font-weight:700;color:var(--p);margin-bottom:6px;}}
  .obj-col ul{{margin:0;padding-left:18px;font-size:14px;}}
  .kirk-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;}}
  .kirk-card{{border:1px solid #E5E7EB;border-radius:10px;padding:12px 14px;background:var(--card);}}
  .kirk-title{{font-weight:700;color:var(--p);margin-bottom:4px;font-size:14px;}}
  .kirk-body{{font-size:14px;}}
  .res-grid{{display:flex;gap:16px;flex-wrap:wrap;font-size:14px;}}
  .res-grid ul{{margin:4px 0;padding-left:18px;}}
  .todo{{background:#FFF7ED;border:1px solid #FDBA74;border-radius:10px;padding:14px 18px;}}
  .todo h2{{border-color:#FDBA74;color:#C2410C;}}
  .todo-list{{margin:6px 0;padding-left:20px;}}
  .footer{{margin-top:40px;color:var(--mute);font-size:12px;text-align:center;}}
</style></head>
<body><div class="wrap">
  <div class="cover"><h1>{esc(title)}</h1><div class="sub">质量培训策划技能 · 输出报告（双版本网页版）</div></div>
  <section><h2>封面与元信息</h2><table class="kv">{meta_rows}</table></section>
  {bg_html}
  {obj_section}
  {outline_section}
  {td_section}
  {asm_section}
  {tr_section}
  {res_section}
  {kirk_section}
  {todo_html}
  <div class="footer">本报告由质量培训策划技能自动生成 · 企业专属内容请按「待企业补充」项完善后使用</div>
</div></body></html>'''


def main():
    ap = argparse.ArgumentParser(description="质量培训策划报告生成器")
    ap.add_argument("--input", required=True, help="方案 JSON 路径")
    ap.add_argument("--md-out", required=True, help="输出 Markdown 路径")
    ap.add_argument("--html-out", required=True, help="输出 HTML 路径")
    args = ap.parse_args()

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        sys.stderr.write(f"[错误] 无法解析输入数据: {e}\n")
        sys.exit(2)

    md = build_md(data)
    html_out = build_html(data)

    with open(args.md_out, "w", encoding="utf-8") as f:
        f.write(md)
    with open(args.html_out, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"[完成] MD  -> {args.md_out}")
    print(f"[完成] HTML-> {args.html_out}")


if __name__ == "__main__":
    main()
