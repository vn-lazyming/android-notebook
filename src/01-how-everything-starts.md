# How everything starts

    Source read at:  AOSP android16-release (99b01a65c, 2025-05-07)
    Device:          SM-S942B · S942BXXS4AZG5 · Android 16
    Device-verified: no — section 6 lists the commands, outputs not pasted yet

Android has no `main()` you can point at. Ask where an app starts and the answer is a
manifest entry; ask where a system service starts and the answer is a line in a 3680-line
Java method; ask where that Java method starts and you end up at a C++ process that
`fork`ed from another C++ process.

There is exactly one place the chain bottoms out, and this chapter walks it from there to
a running phone.

## 1. Why init exists

The kernel finishes booting and has nothing to do. It has no concept of a service, a
property, an app or a user. Its last act is `execve` on one userspace binary, and
everything that makes the machine an Android phone is built by that binary and its
descendants.

On Android that binary is `init`, and it is PID 1. Two consequences worth holding onto:

- **every process on the phone is a descendant of init.** There is no other root of the
  tree. `zygote`, `servicemanager`, `rild`, your app — all of them.
- **init never exits.** If it did, the kernel would panic. It ends in an infinite event
  loop, and that loop is what restarts a service when it dies.

## 2. One binary, three runs

The first surprise: `init` runs three times, and it is the same file each time. It
re-`execve`s itself and decides what to be by looking at its own arguments.

`system/core/init/main.cpp:53`

```
main.cpp:62   argv[0] is "ueventd"        -> ueventd_main()
        :74   argv[1] == "selinux_setup"  -> SetupSelinux()
        :78   argv[1] == "second_stage"   -> SecondStageMain()
        :82   no argv[1]                  -> FirstStageMain()   <- the first run lands here
```

Why re-exec instead of just calling the next function? Because stage 2 loads the SELinux
policy. A process cannot change its own SELinux domain while running — the domain is
assigned at `execve`. So init has to restart itself to come back in the right domain.

That is the whole trick, and it explains the odd shape of the file.

## 3. Stage 1 — `FirstStageMain()`

`system/core/init/first_stage_init.cpp`. At this point there is no `/dev`, no `/proc`,
nothing. It builds the minimum by hand:

```c
mount("tmpfs", "/dev", "tmpfs", MS_NOSUID, "mode=0755");
mount("proc",  "/proc", "proc", 0, "hidepid=2,gid=" MAKE_STR(AID_READPROC));
mount("sysfs", "/sys", "sysfs", 0, NULL);
mount("selinuxfs", "/sys/fs/selinux", "selinuxfs", 0, NULL);
mknod("/dev/kmsg", ...);  mknod("/dev/null", ...);
mknod("/dev/random", ...); mknod("/dev/urandom", ...);
```

Note `hidepid=2` on `/proc`. That mount option is the reason an app cannot read
`/proc/<pid>` of another process. It is decided here, in the first twenty lines of
userspace — not by SELinux, not by a permission, not by the framework.

Then it mounts the real partitions (`DoFirstStageMount`) and re-execs itself with
`selinux_setup`.

## 4. Stage 2 — `SetupSelinux()`

Loads the policy into the kernel, switches to enforcing, re-execs itself with
`second_stage`.

**From this moment SELinux is on.** Everything that follows is gated. There is no window
during boot where userspace runs with SELinux disabled.

## 5. Stage 3 — `SecondStageMain()`

`system/core/init/init.cpp:960`. This is the one that builds the system. In order:

```
Epoll epoll                            the event loop
StartPropertyService(&property_fd)     setprop / getprop become available
LoadBootScripts(am, sm)                parse EVERY .rc file -> services + actions
am.QueueEventTrigger("early-init")
am.QueueEventTrigger("init")
am.QueueEventTrigger("late-init")
while (true) { am.ExecuteOneCommand(); epoll.Wait(); }
```

`LoadBootScripts` reads every `.rc` on the device — including the vendor ones, including
`vendor.samsung.rild.rc`. Nothing is started yet; it is a list in memory.

init does not start services directly. It queues **triggers**, and a service starts when
the trigger naming its class fires.

### The trigger chain

`system/core/rootdir/init.rc`

```
:15    on early-init
:103   on init
:501   on late-init
:502       trigger early-fs
:509       trigger post-fs
:520       trigger post-fs-data
:527       trigger zygote-start
:533       trigger boot
:1088  on zygote-start
:1104  on boot
:1213      class_start hal
:1215      class_start core      <- servicemanager  (class core animation)
:1218      class_start main      <- zygote          (class main)
```

`class_start` is the answer to "what starts everything". init groups services by their
`class` line and one `class_start core` launches every service that declared that class.

`servicemanager` comes up at line 1215, `zygote` at 1218. That ordering is not an accident:
the registry has to exist before anything can register in it.

## 6. From zygote to a running framework

```
system/core/rootdir/init.zygote64.rc:1
    service zygote /system/bin/app_process64 -Xzygote /system/bin \
        --zygote --start-system-server --socket-name=zygote
        class main
        user root
```

`app_process64` is an ordinary C++ program with an ordinary `main()`:

```
frameworks/base/cmds/app_process/app_main.cpp:173   int main(...)
                                              :267   zygote = true          (from --zygote)
                                              :336   runtime.start("com.android.internal.os.ZygoteInit", ...)
```

Line 336 is the native/Java boundary. `AndroidRuntime::start()` boots the ART VM inside
this process and calls into a Java class. Before that line there is no Java on the phone.

```
frameworks/base/core/java/com/android/internal/os/ZygoteInit.java:817   main()
                                                                  :885   preload()
                                                                  :282   preloadClasses()
                                                                  :140   Resources.preloadResources()
                                                                  :902   new ZygoteServer(...)
                                                                  :905   forkSystemServer(...)
                                                                  :731   "com.android.server.SystemServer"
                                                                  :780   Zygote.forkSystemServer(...)
```

`preload()` is the entire reason zygote exists: load a few thousand framework classes and
resources **once**, then fork. The child inherits that heap copy-on-write and starts in
tens of milliseconds instead of seconds.

The child of that fork runs:

```
frameworks/base/services/java/com/android/server/SystemServer.java:688   main()
                                                                   :796   run()
                                                                   :894   Looper.prepareMainLooper()
                                                                   :933   ServiceManager.addService("system_server_dumper", ...)
                                                                   :986   startBootstrapServices()
                                                                   :987   startCoreServices()
                                                                   :988   startOtherServices()
                                                                  :1036   Looper.loop()
                                                                  :1037   throw new RuntimeException("Main thread loop unexpectedly exited")
```

`startOtherServices()` alone is ~1980 lines and contains 189 start/add calls.

## 7. The whole chain

```
bootloader
  -> kernel
  -> execve /system/bin/init                    main.cpp:53
       -> FirstStageMain                        mount /dev /proc(hidepid=2) /sys
       -> exec self: selinux_setup              policy loaded, enforcing
       -> exec self: second_stage               init.cpp:960
            -> LoadBootScripts                  every *.rc parsed
            -> trigger early-init / init / late-init
            -> class_start core                 servicemanager
            -> class_start main                 zygote
                 -> ZygoteInit.main()           preload classes + resources
                 -> forkSystemServer()          ZygoteInit.java:905
                      -> SystemServer.main()    SystemServer.java:688
                           -> 189 system services, all in one process, all uid 1000
            -> while(true) epoll                init lives forever, reaps children
```

## 8. What this decides about the attack surface

Five facts fall out of the boot sequence, and each one shapes everything later.

**The `.rc` file is the manifest of the native world.** uid, groups, capabilities and
restart policy are declared there, in plain text, on disk, readable without root:

```
service ril-daemon /vendor/bin/hw/rild
    user radio
    group radio cache inet misc audio log oem_2901 system drmrpc vpn readproc wakelock net_admin
    capabilities BLOCK_SUSPEND NET_ADMIN NET_RAW SYS_ADMIN CHOWN SYS_TIME
```

Reading every `.rc` on the phone gives the privilege of every native process, before any
reversing.

**`system_server` is one process holding 189 services.** No boundary exists between
`ClipboardService` and `PowerManagerService` — same uid 1000, same heap, same address
space. Code execution in one is code execution in all of them.

**A crash in system_server reboots the phone.** `SystemServer.java:1037` throws if the
looper ever exits, init reaps the dead child, and the device restarts. This is why a plain
NPE in any system service is a soft reboot, not a caught exception.

**No process re-randomises after zygote.** Every app and `system_server` are `fork`ed, not
`execve`d, so they share zygote's memory layout: same library base addresses, same
allocator state. An attacker app can read its own `/proc/self/maps` and know where `libc`
sits inside the victim. ASLR does not need to be defeated because it never ran again.

**SELinux is on before any service starts.** There is no early-boot window to exploit from
userspace; stage 2 completes before stage 3 queues a single trigger.

## 9. Verify on device

Not yet run in this session — paste real output under each.

```bash
# init is PID 1, and everything descends from it
adb shell ps -A -o PID,PPID,NAME | head

# every native service, with the uid and capabilities it was granted
adb shell 'grep -rh "^service \|^    user \|^    group \|^    capabilities " \
    /system/etc/init/ /vendor/etc/init/ /system/bin/init'

# the two that matter, and their order
adb shell ps -AZ | grep -E "servicemanager|zygote|system_server"

# 189 services in one process
adb shell service list | wc -l

# proof of hidepid=2
adb shell cat /proc/mounts | grep " /proc "

# boot order as it actually happened
adb shell dmesg | grep -i "init: starting service" | head -40
```

## 10. Traps

**`dumpsys` is not the manifest, and `service list` is not the `.rc`.** Each shows what
registered successfully. A service that failed to start is simply absent, with no error —
`SystemServer.java` only calls `reportWtf` for device-specific services, so a broken OEM
service disappears silently.

**Do not read `init.rc` from AOSP and assume it is the phone's.** The device merges
`/system/etc/init/*.rc`, `/vendor/etc/init/*.rc`, `/odm/...` and APEX `.rc` files. Vendors
add, override (`override` keyword) and reorder. Read the device's, always.

**`class main` is not "the main class".** It is a group label. Services are started in
class groups, and the group name says nothing about importance.

**The AOSP tree read here is months behind the device.** Line numbers in this chapter are
from `android16-release` (2025-05-07); the device runs a later build. Every line number is
a pointer to a mechanism, never evidence about this firmware. When a claim depends on the
exact code, check the phone's own binary.
