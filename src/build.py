#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把一份 JSON 数据打包成单文件看板。

用法（在仓库根目录运行）：

    python src/build.py                          # 用 data/demo.json 生成 index.html
    python src/build.py data/mine.json           # 用自己的数据生成
    python src/build.py data/mine.json out.html  # 指定输出文件名

生成的 HTML 是单文件，数据已内嵌，可直接双击打开或丢到任何静态服务器上。
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, 'src', 'template.html')
DEFAULT_IN = os.path.join(ROOT, 'data', 'demo.json')
DEFAULT_OUT = os.path.join(ROOT, 'index.html')

LEVELS = ('g', 'l', 'y', 'r')


def die(msg):
    print('错误：' + msg, file=sys.stderr)
    sys.exit(1)


def validate(d):
    """校验数据结构，返回错误列表。"""
    errs = []
    if not isinstance(d, dict):
        return ['顶层必须是一个 JSON 对象']
    recs = d.get('records')
    if not isinstance(recs, list) or not recs:
        return ['缺少 records 数组，或数组为空']

    for i, r in enumerate(recs, 1):
        if not isinstance(r, dict):
            errs.append('第 %d 条不是对象' % i)
            continue
        if not r.get('name'):
            errs.append('第 %d 条缺少 name' % i)
        lv = r.get('level')
        if not lv:
            errs.append('第 %d 条缺少 level' % i)
        elif lv not in LEVELS:
            errs.append('第 %d 条的 level 必须是 g/l/y/r，当前为 %r' % (i, lv))
        for k in ('a1', 'a2', 'a3'):
            v = r.get(k, -1)
            if v not in (1, 0, -1):
                errs.append('第 %d 条的 %s 必须是 1（已完成）/ 0（明确未完成）/ -1（未记录），当前为 %r' % (i, k, v))
        lc = r.get('lastContact', -1)
        if not isinstance(lc, int) or isinstance(lc, bool) or lc < -1:
            errs.append('第 %d 条的 lastContact 必须是 -1（未记录）或非负整数（天数），当前为 %r' % (i, lc))
        if len(errs) > 20:
            errs.append('……还有更多错误，先修完这些')
            break

    docs = d.get('docs')
    if docs is not None and not isinstance(docs, dict):
        errs.append('docs 必须是对象（以记录 id 为 key）')

    ids = {r.get('id') for r in recs if isinstance(r, dict)}
    if None in ids:
        errs.append('有记录缺少 id（id 是关联原始资料的主键，必须唯一）')
    if len(ids) != len(recs):
        errs.append('id 有重复，无法唯一关联原始资料')

    return errs


def summarize(d):
    recs = d['records']
    docs = d.get('docs') or {}
    by_level = {k: sum(1 for r in recs if r.get('level') == k) for k in LEVELS}
    linked = sum(1 for r in recs if docs.get(r.get('id')))
    print('  记录数        %d' % len(recs))
    print('  分级分布      g=%d  l=%d  y=%d  r=%d' % (by_level['g'], by_level['l'], by_level['y'], by_level['r']))
    print('  带原始资料    %d / %d' % (linked, len(recs)))
    ups = sorted(x for x in (r.get('updatedAt') for r in recs) if x)
    if ups:
        print('  数据范围      %s ~ %s' % (ups[0], ups[-1]))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    in_path = args[0] if len(args) > 0 else DEFAULT_IN
    out_path = args[1] if len(args) > 1 else DEFAULT_OUT

    if not os.path.isabs(in_path):
        in_path = os.path.join(ROOT, in_path)
    if not os.path.isabs(out_path):
        out_path = os.path.join(ROOT, out_path)

    if not os.path.exists(in_path):
        die('找不到数据文件：%s' % in_path)
    if not os.path.exists(TEMPLATE):
        die('找不到模板文件：%s' % TEMPLATE)

    with open(in_path, encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            die('JSON 解析失败：%s' % e)

    errs = validate(data)
    if errs:
        print('数据校验未通过，共 %d 处：' % len(errs), file=sys.stderr)
        for e in errs:
            print('  · ' + e, file=sys.stderr)
        sys.exit(1)

    print('数据：%s' % os.path.relpath(in_path, ROOT))
    summarize(data)

    with open(TEMPLATE, encoding='utf-8') as f:
        tpl = f.read()
    if '__DATA__' not in tpl:
        die('模板里找不到 __DATA__ 占位符，无法注入数据')

    # 转义 < 和 >，避免数据里出现 </script> 之类的序列破坏 HTML
    payload = (json.dumps(data, ensure_ascii=False, separators=(',', ':'))
               .replace('<', '\\u003c').replace('>', '\\u003e'))

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(tpl.replace('__DATA__', payload))

    size = os.path.getsize(out_path)
    print('\n已生成：%s（%.0f KB）' % (os.path.relpath(out_path, ROOT), size / 1024))
    print('双击打开即可使用。')


if __name__ == '__main__':
    main()
