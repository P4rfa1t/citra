#!/usr/bin/env python3
"""给 libressl 的 .c 强制注入 namespace 头。

libressl 正常构建时由 autotools/CMake 用 -include 注入
crypto/hidden/crypto_namespace.h 和 ssl/hidden/ssl_namespace.h，
citra 的 Makefile 直接列出源文件编译，漏了这一步，导致
LCRYPTO_ALIAS / LSSL_ALIAS 等宏未定义。

用法: inject-namespace-header.py <libressl根> <相对头1> [相对头2 ...]
"""
import os
import sys

root = os.path.abspath(sys.argv[1])
headers = [os.path.join(root, h) for h in sys.argv[2:]]

for h in headers:
    if not os.path.exists(h):
        sys.exit("找不到头文件: %s" % h)

# 引号包含会先按源文件目录解析，深层文件用相对路径会失败，用绝对路径最稳
lines = ['#include "%s"\n' % h.replace(os.sep, "/") for h in headers]
marker = os.path.basename(headers[0])

n = 0
skipped = 0
for dirpath, _dirs, files in os.walk(root):
    for f in sorted(files):
        if not f.endswith(".c"):
            continue
        p = os.path.join(dirpath, f)
        with open(p, encoding="utf-8", errors="surrogateescape") as fh:
            head = fh.read(3000)
        if marker in head:
            skipped += 1
            continue
        with open(p, "r+", encoding="utf-8", errors="surrogateescape") as fh:
            body = fh.read()
            fh.seek(0)
            fh.write("".join(lines) + body)
        n += 1

print("injected %d headers into %d files (skipped %d)" % (len(lines), n, skipped))
