#!/usr/bin/env python3
"""给 libressl 的所有 .c 强制注入 crypto_namespace.h。

libressl 正常构建时由 autotools/CMake 用 -include 注入这个头，
citra 的 Makefile 直接列出源文件编译，漏了这一步，导致
LCRYPTO_ALIAS / LCRYPTO_USED 等宏未定义。
这里在每个 .c 开头补一行 #include。
"""
import os
import sys

header = sys.argv[1]
roots = sys.argv[2:]
# 以 libressl 根目录为基准算相对路径
libressl_root = os.path.commonpath([os.path.abspath(r) for r in roots])
line = '#include "%s"\n' % os.path.relpath(
    os.path.abspath(header), libressl_root).replace(os.sep, "/")

n = 0
skipped = 0
files_to_scan = []
for root in roots:
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f.endswith(".c"):
                files_to_scan.append(os.path.join(dirpath, f))

for p in files_to_scan:
    with open(p, encoding="utf-8", errors="surrogateescape") as fh:
        head = fh.read(2000)
    if "crypto_namespace.h" in head:
        skipped += 1
        continue
    with open(p, "r+", encoding="utf-8", errors="surrogateescape") as fh:
        body = fh.read()
        fh.seek(0)
        fh.write(line + body)
    n += 1

print(f"injected {line.strip()} into {n} files (skipped {skipped})")
