#!/bin/bash
# installs counterd on the cuttlefish device, policy included.
# run ./build.sh first. safe to re-run: every step is guarded.
#
# what it does, and why each step is needed:
#   1 push the binary and the .rc                 init needs both
#   2 append counterd.cil to plat_sepolicy.cil    gives us a domain + a service type
#   3 add one line to plat_file_contexts          maps the binary to counterd_exec
#   4 add one line to plat_service_contexts       maps the service name to counterd_service,
#                                                 inserted BEFORE the `*` catch-all or it loses
#   5 move precompiled_sepolicy aside             else init ignores our .cil edits
#   6 reboot                                      no way to make init reload a .rc or policy live
#   7 restorecon the binary                       file_contexts does NOT relabel existing files,
#                                                 the label lives in the xattr
#   8 start counterd
set -eu

SM=/system/etc/selinux
dev() { adb shell "$@"; }

[ -f counterd ] || { echo "no counterd binary, run ./build.sh"; exit 1; }

adb root >/dev/null 2>&1 || true
sleep 2
adb remount >/dev/null

echo "[1] binary + rc"
adb push counterd    /system/bin/        >/dev/null
adb push counterd.rc /system/etc/init/   >/dev/null
dev chmod 755 /system/bin/counterd
dev chmod 644 /system/etc/init/counterd.rc

echo "[2] sepolicy"
if dev "grep -q '(type counterd)' $SM/plat_sepolicy.cil"; then
    echo "    already there"
else
    adb pull $SM/plat_sepolicy.cil /tmp/plat.cil >/dev/null
    cat /tmp/plat.cil counterd.cil > /tmp/plat_new.cil
    adb push /tmp/plat_new.cil $SM/plat_sepolicy.cil >/dev/null
    rm -f /tmp/plat.cil /tmp/plat_new.cil
fi

echo "[3] file_contexts"
dev "grep -q 'bin/counterd' $SM/plat_file_contexts || \
     echo '/system/bin/counterd       u:object_r:counterd_exec:s0' >> $SM/plat_file_contexts"

echo "[4] service_contexts"
dev "grep -q 'com.example.ICounter' $SM/plat_service_contexts || \
     sed -i 's|^\*  *u:object_r:default_android_service:s0|com.example.ICounter/default              u:object_r:counterd_service:s0\n*                                         u:object_r:default_android_service:s0|' $SM/plat_service_contexts"

echo "[5] precompiled_sepolicy aside"
dev '[ -f /odm/etc/selinux/precompiled_sepolicy ] && \
     mv /odm/etc/selinux/precompiled_sepolicy /odm/etc/selinux/precompiled_sepolicy.bak || true'

echo "[6] reboot"
adb reboot
sleep 60
for i in $(seq 1 30); do
    adb connect localhost:6520 >/dev/null 2>&1 || true
    [ "$(dev getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ] && break
    sleep 8
done

adb root >/dev/null 2>&1 || true
sleep 2
adb remount >/dev/null

echo "[7] restorecon"
dev restorecon /system/bin/counterd
dev 'ls -lZ /system/bin/counterd'

echo "[8] start"
dev start counterd
sleep 3
dev 'getprop init.svc.counterd'
dev 'ps -AZ | grep counterd'
adb shell service check com.example.ICounter/default
