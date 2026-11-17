#!/usr/bin/env python3
"""给 citra 自带的 libressl 打 libnx 适配补丁。

libressl 的 compat 层默认假设「非 Windows 平台一定有 <syslog.h>」，
而 libnx 既没有这个头，也没有 LOG_* 常量。
直接把 include_next 去掉，强制走 libressl 自带的常量与结构体定义。
"""
import sys

p = sys.argv[1]
s = open(p).read()

old_inc = "#ifndef _WIN32\n#include_next <syslog.h>\n#endif"
new_inc = "/* libnx: 没有 <syslog.h>，直接使用本文件自带定义 */\n#define HAVE_SYSLOG_H 0"
if old_inc not in s:
    print("syslog.h 的 include_next 结构与预期不符，跳过")
    sys.exit(0)

s = s.replace(old_inc, new_inc, 1)
# 让 LOG_* 常量无条件可用（原来只给 _WIN32）
s = s.replace("#ifdef _WIN32\n#define\tLOG_INFO", "#if 1 /* libnx: 无系统 syslog */\n#define\tLOG_INFO", 1)
open(p, "w").write(s)
print("patched:", p)
