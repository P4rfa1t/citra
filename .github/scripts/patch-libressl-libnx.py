#!/usr/bin/env python3
"""给 citra 自带的 libressl 打 libnx 适配补丁。

libressl 的 compat 层是一堆 `#include_next <xxx.h>` 垫片，默认假设宿主平台
有完整的 POSIX/BSD 头。libnx 是裸机 SDK，缺其中一部分，include_next 会
直接 fatal error。

注意：devkitA64 的 gcc 对 __has_include(<syslog.h>) 判定不可靠（实测返回真
但头并不存在），所以不能靠它。这里用显式的「libnx 缺失清单」。
"""
import os
import re
import sys

# libnx / devkitPro portlibs 里确实没有的头。
# 加进来就把 include_next 整行删掉，让 libressl 用自己的定义。
MISSING_ON_LIBNX = {
    "syslog.h",
    "endian.h",
    "machine/endian.h",
}

INCLUDE_NEXT = re.compile(r'^#\s*include_next\s*<([^>]+)>.*$')


def patch_header(p):
    s = open(p, encoding="utf-8", errors="surrogateescape").read()
    if "LIBNX_INCLUDE_NEXT_HANDLED" in s:
        return False

    out = []
    changed = False
    for line in s.split("\n"):
        m = INCLUDE_NEXT.match(line)
        if m and m.group(1) in MISSING_ON_LIBNX:
            out.append("/* LIBNX_INCLUDE_NEXT_HANDLED: libnx 无 <%s>，跳过 */"
                       % m.group(1))
            changed = True
        else:
            out.append(line)

    if changed:
        s = "\n".join(out)
        open(p, "w", encoding="utf-8", errors="surrogateescape").write(s)
    return changed


def patch_time_clockid(p):
    s = open(p, encoding="utf-8", errors="surrogateescape").read()
    if "LIBNX_CLOCK_SHIM" in s or "typedef int clockid_t;" not in s:
        return False
    s = ("/* LIBNX_CLOCK_SHIM: libnx 的 clockid_t 已由 newlib 提供 */\n"
         "#ifndef HAVE_CLOCK_GETTIME\n#define HAVE_CLOCK_GETTIME 1\n#endif\n") + s
    open(p, "w", encoding="utf-8", errors="surrogateescape").write(s)
    return True


def patch_syslog_consts(p):
    s = open(p, encoding="utf-8", errors="surrogateescape").read()
    if "LIBNX_SYSLOG_CONSTS" in s:
        return False
    if "#ifdef _WIN32\n#define\tLOG_INFO" not in s:
        return False
    s = s.replace("#ifdef _WIN32\n#define\tLOG_INFO",
                  "/* LIBNX_SYSLOG_CONSTS */\n#if 1\n#define\tLOG_INFO", 1)
    open(p, "w", encoding="utf-8", errors="surrogateescape").write(s)
    return True


def patch_endian_macros(p):
    """libnx 的 newlib 没有 <endian.h>，所以 htobe32/be64toh 等宏全缺。
    用 GCC 内建 __builtin_bswap* 补齐（常量折叠，零开销）。"""
    s = open(p, encoding="utf-8", errors="surrogateescape").read()
    if "LIBNX_ENDIAN_MACROS" in s:
        return False
    block = (
        "\n/* LIBNX_ENDIAN_MACROS: libnx 无 <endian.h>，用 GCC bswap 内建补齐 */\n"
        "#if defined(__SWITCH__)\n"
        "#include <stdint.h>\n"
        "#define bswap16(x) __builtin_bswap16((uint16_t)(x))\n"
        "#define bswap32(x) __builtin_bswap32((uint32_t)(x))\n"
        "#define bswap64(x) __builtin_bswap64((uint64_t)(x))\n"
        "#ifndef htobe16\n#define htobe16(x) bswap16(x)\n#endif\n"
        "#ifndef htobe32\n#define htobe32(x) bswap32(x)\n#endif\n"
        "#ifndef htobe64\n#define htobe64(x) bswap64(x)\n#endif\n"
        "#ifndef be16toh\n#define be16toh(x) bswap16(x)\n#endif\n"
        "#ifndef be32toh\n#define be32toh(x) bswap32(x)\n#endif\n"
        "#ifndef be64toh\n#define be64toh(x) bswap64(x)\n#endif\n"
        "#ifndef htole16\n#define htole16(x) ((uint16_t)(x))\n#endif\n"
        "#ifndef htole32\n#define htole32(x) ((uint32_t)(x))\n#endif\n"
        "#ifndef htole64\n#define htole64(x) ((uint64_t)(x))\n#endif\n"
        "#ifndef le16toh\n#define le16toh(x) ((uint16_t)(x))\n#endif\n"
        "#ifndef le32toh\n#define le32toh(x) ((uint32_t)(x))\n#endif\n"
        "#ifndef le64toh\n#define le64toh(x) ((uint64_t)(x))\n#endif\n"
        "#endif\n"
    )
    open(p, "w", encoding="utf-8", errors="surrogateescape").write(s + block)
    return True


def patch_posix_shim(p):
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
    compat_dir, libressl_root = sys.argv[1], sys.argv[2]

    n = 0
    for f in sorted(os.listdir(compat_dir)):
        if f.endswith(".h") and patch_header(os.path.join(compat_dir, f)):
            print("  include_next dropped:", f)
            n += 1

    for f, fn in (("time.h", patch_time_clockid), ("syslog.h", patch_syslog_consts),
                  ("endian.h", patch_endian_macros)):
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
