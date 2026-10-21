# -*- coding: utf-8 -*-
"""wholesale 子域 GSC 实测：属性是否存在 + 曝光/点击/收录趋势。
用法: python .workbuddy/scripts/gsc_wholesale_probe.py
输出: .workbuddy/data/gsc-wholesale-probe.json
"""
import os, sys, json, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import gsc_api_client as G

OUT = os.path.join(PROJ, '.workbuddy', 'data', 'gsc-wholesale-probe.json')
END = datetime.date.today()
START = END - datetime.timedelta(days=120)


def main():
    if not G.is_configured():
        print('GSC 未配置')
        return 1
    svc = G.build_service(G.load_credentials())

    print('=== 1. 账号下全部 GSC 属性 ===')
    props = []
    try:
        lst = svc.sites().list().execute()
        for e in lst.get('siteEntry', []):
            props.append({'siteUrl': e.get('siteUrl'), 'perm': e.get('permissionLevel')})
            print(f"  {e.get('siteUrl'):52s} {e.get('permissionLevel')}")
    except Exception as ex:
        print('  sites.list 失败:', type(ex).__name__, str(ex)[:200])

    result = {'props': props, 'fetched_at': datetime.datetime.now().isoformat(timespec='seconds')}

    # 逐属性查曝光
    print('\n=== 2. 各属性近 120 天表现 ===')
    rows = []
    for p in props:
        u = p['siteUrl']
        try:
            r = G.fetch_search_analytics(u, START.isoformat(), END.isoformat(), row_limit=1)
            tot = r.get('totals') or {}
            # 页面级：有曝光的独立页
            pr = G.fetch_search_analytics(u, START.isoformat(), END.isoformat(), row_limit=25000)
            pages = pr.get('rows') or []
            rows.append({'siteUrl': u,
                         'clicks': tot.get('clicks'), 'impressions': tot.get('impressions'),
                         'ctr': tot.get('ctr'), 'position': tot.get('position'),
                         'pages_with_impr': len(pages)})
            print(f"  {u:52s} clicks={tot.get('clicks')} impr={tot.get('impressions')} "
                  f"pages={len(pages)} pos={tot.get('position')}")
        except Exception as ex:
            rows.append({'siteUrl': u, 'error': f'{type(ex).__name__}: {str(ex)[:150]}'})
            print(f"  {u:52s} ERR {type(ex).__name__}: {str(ex)[:120]}")
    result['perf'] = rows

    # wholesale 专属：sitemap 状态
    print('\n=== 3. wholesale sitemap 提交状态 ===')
    sm = []
    for p in props:
        if 'wholesale' not in p['siteUrl']:
            continue
        try:
            resp = svc.sitemaps().list(siteUrl=p['siteUrl']).execute()
            for e in resp.get('sitemap', []):
                d = e.get('lastSubmitted')
                d = d[:10] if d else None
                sm.append({'path': e.get('path'), 'lastSubmitted': d,
                           'isPending': e.get('isPending'), 'isSitemapsIndex': e.get('isSitemapsIndex'),
                           'warnings': e.get('warnings'), 'errors': e.get('errors'),
                           'contents': e.get('contents')})
                print(f"  {e.get('path')}")
                print(f"    lastSubmitted={d} errors={e.get('errors')} warnings={e.get('warnings')}")
                for c in (e.get('contents') or []):
                    print(f"      {c.get('type')} submitted={c.get('submitted')} indexed={c.get('indexed')}")
        except Exception as ex:
            print('  ', type(ex).__name__, str(ex)[:180])
    result['wholesale_sitemaps'] = sm

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(result, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'\n已写入 {OUT}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
