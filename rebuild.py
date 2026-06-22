#!/usr/bin/env python3
"""Rebuild HTML articles from markdown and push to GitHub."""
import os, base64, json, urllib.request, ssl, re
from pathlib import Path

def load_github_token():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token.strip()
    token_file = Path(r"D:\AI项目\账号密码\tokens\github-fine-grained-token.md")
    if token_file.exists():
        for line in token_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("github_pat_"):
                return line.strip()
            if line.upper().startswith("GITHUB_TOKEN="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("Missing GitHub token. Set GITHUB_TOKEN/GH_TOKEN or update D:\\AI项目\\账号密码\\tokens\\github-fine-grained-token.md")


TOKEN = load_github_token()
OWNER = "shujian2605"
REPO = "bestlinkchip-tech"
ART_DIR = r"D:\AI项目\佳联芯品牌推广\知乎文章"
OUT_DIR = r"D:\AI项目\佳联芯品牌推广\website\articles"

HTML_TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link rel="stylesheet" href="../style.css">
</head>
<body>
<header>
  <div class="container">
    <a href="../index.html" class="logo">佳联芯科技</a>
    <nav>
      <a href="../solutions.html">方案中心</a>
      <a href="../blog.html">技术博客</a>
      <a href="../about.html">关于我们</a>
      <a href="../contact.html">联系我们</a>
    </nav>
  </div>
</header>
<main class="container">
<article>
{body}
</article>
</main>
<footer>
  <div class="container">
    <p>&copy; 2026 深圳佳联芯科技有限公司 | 专注、专业、专一、杰理16年</p>
  </div>
</footer>
</body>
</html>"""


def api(method, path, data=None):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/{path}"
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    body = None
    if data:
        body = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    ctx = ssl.create_default_context()
    try:
        res = urllib.request.urlopen(req, body, context=ctx, timeout=30)
        if res.status == 204:
            return None
        return json.loads(res.read())
    except urllib.error.HTTPError as e:
        content = e.read().decode()
        raise Exception(f"API {method} {path} -> {e.code}: {content}")


def md2html(md_text):
    lines = md_text.strip().split("\n")
    parts = []
    in_table = False
    has_open_p = False

    for line in lines:
        s = line.strip()

        if not s:
            if has_open_p:
                parts.append("</p>")
                has_open_p = False
            continue

        if s.startswith("```"):
            if has_open_p:
                parts.append("</p>")
                has_open_p = False
            tag = "<pre><code>" if s == "```" else "</code></pre>"
            parts.append(tag)
            continue

        if s.startswith("|") and _next_is_sep(lines, line):
            continue

        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not in_table:
                parts.append("<table>")
                in_table = True
                row = "<tr>" + "".join(f"<th>{c}</th>" for c in cells) + "</tr>"
            else:
                row = "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"
            parts.append(row)
            continue
        elif in_table:
            parts.append("</table>")
            in_table = False

        if s.startswith("# "):
            parts.append(f"<h1>{s[2:]}</h1>")
            continue
        if s.startswith("## "):
            parts.append(f"<h2>{s[3:]}</h2>")
            continue
        if s.startswith("### "):
            parts.append(f"<h3>{s[4:]}</h3>")
            continue
        if s.startswith("> "):
            parts.append(f"<blockquote>{s[2:]}</blockquote>")
            continue
        if s == "---":
            parts.append("<hr>")
            continue

        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)

        if not has_open_p:
            parts.append("<p>")
            has_open_p = True
        else:
            parts.append("<br>")
        parts.append(s)

    if has_open_p:
        parts.append("</p>")
    if in_table:
        parts.append("</table>")

    return "\n".join(parts)


def _next_is_sep(lines, current):
    found = False
    for l in lines:
        if found and l.strip().startswith("|"):
            return "---" in l
        if l == current:
            found = True
    return False


slug_map = {
    "01_杰理芯片选型指南2026_QC.md": "jl-chip-guide",
    "02_新国标移动电源PCBA方案怎么选_QC.md": "gb47372-powerbank",
    "03_BOM报价背后的PCBA供应链逻辑_QC.md": "bom-supplychain",
    "04_蓝牙耳机TWS技术演进_QC.md": "tws-evolution",
    "05_PCBA方案商怎么帮品牌方省钱_QC.md": "rd-cost-saving",
}

titles = {
    "01": "杰理芯片选型指南2026 - 佳联芯科技",
    "02": "新国标移动电源PCBA方案怎么选 - 佳联芯科技",
    "03": "BOM报价背后的PCBA供应链逻辑 - 佳联芯科技",
    "04": "蓝牙耳机TWS技术演进 - 佳联芯科技",
    "05": "PCBA方案商怎么帮品牌方省钱 - 佳联芯科技",
}

os.makedirs(OUT_DIR, exist_ok=True)

for fname, slug in slug_map.items():
    fpath = os.path.join(ART_DIR, fname)
    if not os.path.exists(fpath):
        print(f"MISSING: {fname}")
        continue
    with open(fpath, "r", encoding="utf-8") as f:
        md = f.read()
    num = fname[:2]
    title = titles.get(num, fname)
    body = md2html(md)
    html = HTML_TPL.format(title=title, body=body)
    out_path = os.path.join(OUT_DIR, f"{slug}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML: {slug}.html ({len(html)} chars)")

    # Push
    try:
        existing = api("GET", f"contents/articles/{slug}.html")
        sha = existing["sha"]
        data = {
            "message": f"Update {title}",
            "content": base64.b64encode(html.encode("utf-8")).decode(),
            "branch": "main",
            "sha": sha,
        }
        api("PUT", f"contents/articles/{slug}.html", data)
        print(f"  PUSHED: articles/{slug}.html")
    except Exception as e:
        print(f"  FAIL: {str(e)[:150]}")

print("\nDone!")
