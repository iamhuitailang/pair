#!/usr/bin/env python3
"""模拟样例站点内容变化，用于演示变更追踪。

用法：
    python3 change_site.py apply     制造变化：修改资料二、下线资料三、新增资料八
    python3 change_site.py restore   恢复站点原状
"""
import shutil
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent
BACKUP = SITE.parent / ".sample_site_original"

ARTICLE_8 = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>资料八：导出格式说明 · 本地资料站</title>
  <link rel="stylesheet" href="/style.css">
</head>
<body>
  <header class="site">
    <h1>资料八：导出格式说明</h1>
    <nav>
      <a href="/index.html">首页</a>
      <a href="/news/index.html">资料列表</a>
      <a href="/about.html">关于本站</a>
    </nav>
  </header>
  <main class="content">
    <p>这是变更脚本新增的文章，用于演示 new 状态。</p>
    <p>JSON 导出包含运行元信息与全部页面快照；CSV 导出便于表格软件查看。</p>
  </main>
  <p class="updated">更新时间：2026-11-12 10:00</p>
  <footer>Local Demo Site · 仅供本机演示</footer>
</body>
</html>
"""

NEW_ITEM_8 = """    <article class="item">
      <h2><a href="/news/article-8.html">资料八：导出格式说明</a></h2>
      <p class="updated">更新时间：2026-11-12 10:00</p>
    </article>
  </main>"""


def apply():
    if not BACKUP.exists():
        shutil.copytree(SITE, BACKUP)
        print(f"已备份原始站点到 {BACKUP}")

    # 1) 修改资料二：改一段正文 + 更新时间
    p2 = SITE / "news" / "article-2.html"
    text = p2.read_text(encoding="utf-8")
    text = text.replace(
        "上一轮存在而本轮未访问到的 URL 记为 disappeared，即页面可能已下线。",
        "上一轮存在而本轮未访问到的 URL 记为 disappeared；本段为修订内容："
        "被修改页面的 diff 可在运行详情页逐行查看。")
    text = text.replace("更新时间：2026-10-22 14:30", "更新时间：2026-11-12 09:30")
    p2.write_text(text, encoding="utf-8")
    print("已修改 news/article-2.html（内容 + 更新时间）")

    # 2) 下线资料三：删除文章并从列表移除链接
    p3 = SITE / "news" / "article-3.html"
    if p3.exists():
        p3.unlink()
    idx = SITE / "news" / "index.html"
    text = idx.read_text(encoding="utf-8")
    start = text.find('    <article class="item">\n      <h2><a href="/news/article-3.html"')
    if start != -1:
        end = text.find("</article>", start) + len("</article>\n")
        text = text[:start] + text[end:]
    idx.write_text(text, encoding="utf-8")
    print("已下线 news/article-3.html（删除文件并移除列表链接）")

    # 3) 新增资料八：新建文章并加入第 2 页列表
    (SITE / "news" / "article-8.html").write_text(ARTICLE_8, encoding="utf-8")
    pg2 = SITE / "news" / "page2.html"
    text = pg2.read_text(encoding="utf-8")
    if "article-8" not in text:
        text = text.replace("  </main>", NEW_ITEM_8, 1)
    pg2.write_text(text, encoding="utf-8")
    print("已新增 news/article-8.html 并加入列表第 2 页")

    print("\n变化就绪：1 篇修改、1 篇下线、1 篇新增。现在重新运行一轮采集即可看到差异。")


def restore():
    if not BACKUP.exists():
        print("没有找到备份，无需恢复。")
        return
    for item in SITE.iterdir():
        if item.name == Path(__file__).name:
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
    for item in BACKUP.iterdir():
        dest = SITE / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)
    print("站点已恢复为初始状态。")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("apply", "restore"):
        sys.exit(__doc__)
    if sys.argv[1] == "apply":
        apply()
    else:
        restore()
