# -*- coding: utf-8 -*-
"""把 wholesale 聚合页推给 IndexNow（Bing / Yandex / Seznam）。

wholesale 的 GSC 属性是 domain property，sitemaps API 不支持，
所以收录加速主要靠 IndexNow + robots.txt 的 Sitemap 声明。

用法：
    python indexnow_push_wholesale.py          # 推 wholesale 全部聚合页
"""
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WS = r'C:\Users\123\WorkBuddy\wholesale-portal'
KEY_FILE = os.path.join(ROOT, '.workbuddy', 'secrets', 'indexnow-key.txt')
ENDPOINT = 'https://api.indexnow.org/indexnow'
HOST = 'wholesale.global-ucars.com'
SITE = f'https://{HOST}'


def main():
    if not os.path.exists(KEY_FILE):
        print(f'缺 IndexNow key: {KEY_FILE}')
        return 1
    key = open(KEY_FILE, encoding='utf-8').read().strip()
    # key 文件必须能从该 host 根目录取到，否则推送会被拒
    chk = urllib.request.urlopen(urllib.request.Request(
        f'{SITE}/{key}.txt', method='HEAD'), timeout=20)
    if chk.status != 200:
        print(f'key 文件未部署（HTTP {chk.status}）：{SITE}/{key}.txt')
        print('先把 <key>.txt 放到站点根目录再推，否则 IndexNow 会拒绝')
        return 1

    slugs = sorted(d for d in os.listdir(WS)
                   if d.startswith('wholesale-') and
                   os.path.exists(os.path.join(WS, d, 'index.html')))
    urls = [f'{SITE}/'] + [f'{SITE}/{s}/' for s in slugs]

    payload = json.dumps({'host': HOST, 'key': key, 'urlList': urls}).encode()
    req = urllib.request.Request(ENDPOINT, data=payload,
                                 headers={'Content-Type': 'application/json; charset=utf-8'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            print(f'HTTP {r.status}  推送 {len(urls)} 个 URL')
            for u in urls:
                print('  ', u)
            return 0
    except Exception as e:
        print('推送失败:', str(e)[:200])
        return 1


if __name__ == '__main__':
    sys.exit(main())
