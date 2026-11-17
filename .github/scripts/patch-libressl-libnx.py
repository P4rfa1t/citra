#!/usr/bin/env python3
"""给 citra 自带的 libressl 打 libnx 适配补丁。

libressl 的 compat 层默认假设「非 Windows 平台一定有 <syslog.h>」，
而 libnx 既没有这个头文件，也没有 LOG_* 常量。
这里把 include_next 挂到 __has_include 上，缺头时退回自带定义。
"""
import sys

p = sys.argv[1]
s = open(p).read()

old_inc = "#ifndef _WIN32\n#include_next <syslog.h>\n#endif"
new_inc = (
    "#if defined(__has_include)\n"
    "#if __has_include(<syslog.h>)\n"
    "#include_next <syslog.h>\n"
    "#define HAVE_SYSLOG_H 1\n"
    "#endif\n"
    "#else\n"
    "#include_next <syslog.h>\n"
    "#define HAVE_SYSLOG_H 1\n"
    "#endif"
)
if old_inc not in s:
    print("syslog.h 的 include_next 结构与预期不符，跳过")
    sys.exit(0)

s = s.replace(old_inc, new_inc, 1)
s = s.replace("#ifdef _WIN32\n#define\tLOG_INFO", "#if !defined(HAVE_SYSLOG_H)\n#define\tLOG_INFO", 1)
open(p, "w").write(s)
print("patched:", p)
