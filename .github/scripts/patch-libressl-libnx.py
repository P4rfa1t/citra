#!/usr/bin/env python3
"""给 citra 自带的 libressl 打 libnx 适配补丁。

libressl 的 compat 层是一堆 `#include_next <xxx.h>` 的垫片，默认假设
宿主平台有完整的 POSIX/BSD 头。libnx 是裸机 SDK，缺不少（syslog.h、
endian.h 等），include_next 会直接 fatal error。

策略：扫描 compat 目录下所有头，把「无条件 include_next」改成
「只有真的存在时才 include_next」，缺头时退回 libressl 自带定义。
"""
import os
import re
import sys

INCLUDE_NEXT = re.compile(r'^#\s*include_next\s*<([^>]+)>.*$', re.M)


def patch_header(p):
    s = open(p, encoding="utf-8", errors="surrogateescape").read()
    if "LIBNX_NO_INCLUDE_NEXT" in s:
        return False

    out = []
    changed = False
    lines = s.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        m = INCLUDE_NEXT.match(line)
        if m:
            hdr = m.group(1)
            out.append("/* LIBNX_NO_INCLUDE_NEXT: %s 可能不存在 */" % hdr)
            out.append("#if defined(__has_include)")
            out.append("#if __has_include(<%s>)" % hdr)
            out.append("#include_next <%s>" % hdr)
            out.append("#endif")
            out.append("#else")
            out.append("#include_next <%s>" % hdr)
            out.append("#endif")
            changed = True
        else:
            out.append(line)
        i += 1

    if changed:
        open(p, "w", encoding="utf-8", errors="surrogateescape").write("\n".join(out))
    return changed


def patch_time_clockid(p):
    """libnx 的 clockid_t 与 libressl 的 typedef int 冲突。"""
    s = open(p, encoding="utf-8", errors="surrogateescape").read()
    if "LIBNX_CLOCK_SHIM" in s:
        return False
    if "typedef int clockid_t;" not in s:
        return False
    s = ("/* LIBNX_CLOCK_SHIM: libnx 的 clockid_t 已由 newlib 提供 */\n"
         "#ifndef HAVE_CLOCK_GETTIME\n#define HAVE_CLOCK_GETTIME 1\n#endif\n") + s
    open(p, "w", encoding="utf-8", errors="surrogateescape").write(s)
    return True


def patch_syslog_consts(p):
    """让 LOG_* 常量不再只给 Windows。"""
    s = open(p, encoding="utf-8", errors="surrogateescape").read()
    if "LIBNX_SYSLOG_CONSTS" in s:
        return False
    if "#ifdef _WIN32\n#define\tLOG_INFO" not in s:
        return False
    s = s.replace("#ifdef _WIN32\n#define\tLOG_INFO",
                  "/* LIBNX_SYSLOG_CONSTS */\n#if 1\n#define\tLOG_INFO", 1)
    open(p, "w", encoding="utf-8", errors="surrogateescape").write(s)
    return True


def patch_posix_shim(p):
    """bss_bio/bss_conn/bss_dgram 用了 SSIZE_MAX、htons 等，libnx 缺。"""
    s = open(p, encoding="utf-8", errors="surrogateescape").read()
    if "LIBNX_POSIX_SHIM" in s:
        return False
    shim = (
        "/* LIBNX_POSIX_SHIM: newlib/libnx 缺这些定义 */\n"
        "#include <limits.h>\n"
        "#include <sys/types.h>\n"
        "#ifdef __SWITCH__\n"
        "#include <arpa/inet.h>\n"
        "#ifndef SSIZE_MAX\n#define SSIZE_MAX ((ssize_t)(SIZE_MAX >> 1))\n#endif\n"
        "#endif\n"
    )
    open(p, "w", encoding="utf-8", errors="surrogateescape").write(shim + s)
    return True


if __name__ == "__main__":
    compat_dir = sys.argv[1]
    libressl_root = sys.argv[2]

    n = 0
    for f in sorted(os.listdir(compat_dir)):
        if not f.endswith(".h"):
            continue
        p = os.path.join(compat_dir, f)
        if patch_header(p):
            print("  include_next patched:", f)
            n += 1

    for f, fn in (("time.h", patch_time_clockid), ("syslog.h", patch_syslog_consts)):
        p = os.path.join(compat_dir, f)
        if os.path.exists(p) and fn(p):
            print("  extra patched:", f)
            n += 1

    for rel in ("crypto/bio/bss_bio.c", "crypto/bio/bss_conn.c", "crypto/bio/bss_dgram.c"):
        p = os.path.join(libressl_root, rel)
        if os.path.exists(p) and patch_posix_shim(p):
            print("  posix shim:", rel)
            n += 1

    print("total patches:", n)
