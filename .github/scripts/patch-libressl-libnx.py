#!/usr/bin/env python3
"""给 citra 自带的 libressl 打 libnx 适配补丁。

libressl 的 compat 层默认假设「非 Windows 平台一定有 POSIX 环境」，
而 libnx 是个裸机 SDK：既没有 <syslog.h>，clockid_t 的定义也和它的
typedef int 冲突。这里一次性把这两个假设改掉。
"""
import sys


def patch_syslog(p):
    s = open(p).read()
    old = "#ifndef _WIN32\n#include_next <syslog.h>\n#endif"
    new = "/* libnx: 没有 <syslog.h>，直接使用本文件自带定义 */\n#define HAVE_SYSLOG_H 0"
    if old not in s:
        print("  syslog.h: include_next 结构不符，跳过")
        return
    s = s.replace(old, new, 1)
    # 让 LOG_* 常量开销（原来只给 _WIN32）
    s = s.replace("#ifdef _WIN32\n#define\tLOG_INFO",
                  "#if 1 /* libnx: 无系统 syslog */\n#define\tLOG_INFO", 1)
    open(p, "w").write(s)
    print("  patched:", p)


def patch_time(p):
    s = open(p).read()
    marker = "#ifndef HAVE_CLOCK_GETTIME"
    if marker not in s:
        print("  time.h: 结构不符，跳过")
        return
    if "#define HAVE_CLOCK_GETTIME 1" in s:
        print("  time.h: 已打过补丁")
        return
    # 在文件最前面强制声明：libnx 的 clockid_t 已存在且语义正确
    s = "/* libnx: clockid_t/clock_gettime 由 newlib 提供，跳过兼容 typedef */\n" \
        "#ifndef HAVE_CLOCK_GETTIME\n#define HAVE_CLOCK_GETTIME 1\n#endif\n" + s
    open(p, "w").write(s)
    print("  patched:", p)


if __name__ == "__main__":
    patch_syslog(sys.argv[1])
    if len(sys.argv) > 2:
        patch_time(sys.argv[2])
