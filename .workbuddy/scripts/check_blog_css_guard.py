#!/usr/bin/env python3
"""
REGRESSION GUARD — 防止博客页主导航栏因缺主样式表而退化。

检查所有 /blog/*.html：只要页面使用了主站导航（class="navbar"），
就必须包含绝对路径 <link rel="stylesheet" href="/styles.css" />。

用法:
  python .workbuddy/scripts/check_blog_css_guard.py            # 检查，发现broken则 exit 1
  python .workbuddy/scripts/check_blog_css_guard.py --fix       # 自动注入修复后 exit 0

可作为定时任务/发布前 gate 调用。CI 语义：非 0 退出 = 门禁失败。
"""
import os, re, glob, sys, shutil, datetime, json

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # G:/ucars (scripts -> .workbuddy -> ucars)
BLOG = os.path.join(ROOT, "blog")
LINK = '  <link rel="stylesheet" href="/styles.css" />\n</head>'


def main():
    fix = "--fix" in sys.argv
    broken = []
    for p in sorted(glob.glob(os.path.join(BLOG, "*.html"))):
        s = open(p, encoding="utf-8").read()
        has_navbar = bool(re.search(r'class="navbar"', s))
        if not has_navbar:
            continue
        if 'href="/styles.css"' not in s:
            broken.append(p)
            if fix:
                bak = p + ".cssbak"
                if not os.path.exists(bak):
                    shutil.copy2(p, bak)
                s2 = s.replace("</head>", LINK, 1)
                open(p, "w", encoding="utf-8", newline="").write(s2)
    result = {
        "checked_at": datetime.datetime.now().isoformat(),
        "blog_pages": len(glob.glob(os.path.join(BLOG, "*.html"))),
        "broken_count_before": len(broken),
        "broken_pages": [os.path.relpath(p, ROOT).replace("\\", "/") for p in broken],
        "fixed": fix,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if broken and not fix:
        sys.exit(1)  # 门禁失败
    sys.exit(0)


if __name__ == "__main__":
    main()
