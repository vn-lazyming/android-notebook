# How everything starts

lets trace from begining the phone got booting and learn

## in some linux distribution

in the linux kernel, `init` is the first userspace process to be run.

on a normal fedora, ubuntu etc.. machine, init is a symlink to a binary named systemd, which means the first userspace process running in linux is systemd

```console
$ ls -l /sbin/init
/sbin/init -> ../lib/systemd/systemd
$ cat /proc/1/comm
systemd
```

For those who don't know what systemd is: systemd is a process that runs other processes and manages their life cycle.

> they using systemd as a starter for everythings, nothing on a Linux box starts by itself. something has to start it, and that something is PID 1(systemd). every process you will ever see on the machine is a descendant of systemd.

so a vendor or an app can register with systemd to let it control the life cycle automatically for you. for example, when you install ssh it will create a file like this and run `systemctl enable sshd` to let systemd know, so it starts the ssh service when your machine boots, you can also create your too

```ini
; /usr/lib/systemd/system/sshd.service
[Unit]
Description=OpenSSH server daemon
After=network.target sshd-keygen.target
Wants=sshd-keygen.target

[Service]
Type=notify
ExecStart=/usr/sbin/sshd -D $OPTIONS
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=42s

[Install]
WantedBy=multi-user.target
```

## how about in android ?

let's check it

```console
# in my Samsung Galaxy S26
ming@lazy:~ $ adb shell cat /proc/1/comm
init
```

so on android the first userspace process is not systemd. google wrote their own `init` binary instead, it does roughly the same job as systemd but is much smaller and built for a phone. you can read the source here: [system/core/init](https://cs.android.com/android/platform/superproject/main/+/main:system/core/init/), and the `.rc` language reference is [init/README.md](https://cs.android.com/android/platform/superproject/main/+/main:system/core/init/README.md).

in systemd you wrote a unit file you declare what your service needs (After=network.target) and let systemd work out when to run it. in an .rc file you declare when it runs (class main, on boot) and work out the order yourself.

## init reads every .rc file

[`main()`](https://cs.android.com/android/platform/superproject/main/+/main:system/core/init/main.cpp;l=53) at system/core/init/main.cpp is the entry point of the init binary.

```text
main()  argv[1] == "second_stage"          system/core/init/main.cpp:53
 |
 v
SecondStageMain()                         system/core/init/init.cpp:954
 |
 v
LoadBootScripts(am, sm)                   system/core/init/init.cpp:1080
```

init loads all the *.rc files in [`LoadBootScripts()`](https://cs.android.com/android/platform/superproject/main/+/main:system/core/init/init.cpp;l=336) and parses them in to structure and waiting for being executed

```cpp
static void LoadBootScripts(ActionManager& action_manager, ServiceList& service_list) {
    Parser parser = CreateParser(action_manager, service_list);

    std::string bootscript = GetProperty("ro.boot.init_rc", "");
    if (bootscript.empty()) {
        parser.ParseConfig("/system/etc/init/hw/init.rc");
        parser.ParseConfig("/system/etc/init");
        parser.ParseConfig("/system_ext/etc/init");
        parser.ParseConfig("/vendor/etc/init");             // samsung *.rc file folder
        parser.ParseConfig("/odm/etc/init");
        parser.ParseConfig("/product/etc/init");
    } else {
        parser.ParseConfig(bootscript);                      // bootloader override
    }
}
```

## what a .rc file looks like

then, still in `SecondStageMain()`, it starts running all the commands written in the .rc files, example with `tombstone` process bellow.

you will seing some pattern

```sh
on event_name          # event name
    command0           # command to execute
    command1
    command2
```

a command is one of three things. most of them are just a syscall init does itself:

```sh
on init                              # init.rc:103
    symlink /proc/self/fd/0 /dev/stdin
    mkdir /dev/cpuctl/top-app
```

some start a process example with post-fs-data event:

```sh
on post-fs-data                      # init.rc:645
    ...                              # prepare folder for tombstones process
    mkdir /data/tombstones 0775 system system encryption=Require
    mkdir /data/vendor/tombstones 0771 root root
    start tombstoned                 #          :675, start tombstones
```

and some push another event back into the queue, which is how the whole boot is sequenced:

```sh
on late-init                         # init.rc:501
    trigger fs
    trigger post-fs-data
    trigger zygote-start
    trigger boot
```

## the event loop

here is the code that runs them. init drops the first event into the queue at [init.cpp:1135](https://cs.android.com/android/platform/superproject/main/+/main:system/core/init/init.cpp;l=1135), then loops forever at [init.cpp:1143](https://cs.android.com/android/platform/superproject/main/+/main:system/core/init/init.cpp;l=1143).

```cpp
// get all command from late-init event
am.QueueEventTrigger("late-init");   // init.cpp:1135

// execute all command
while (true) {                       // init.cpp:1143
    ...
    if (!(prop_waiter_state.MightBeWaiting() || Service::is_exec_service_running())) {
        am.ExecuteOneCommand();      // one command per iteration
        if (am.HasMoreCommands()) next_action_time = boot_clock::now();
    }
    ...
    epoll.Wait(next_action_time);
}
```

each time around it takes one event out of the queue, finds every `on` block with that name, and runs one command from it.

## what `start` does

`start tombstoned` looks the name up in `ServiceList` and calls [`Service::Start()`](https://cs.android.com/android/platform/superproject/main/+/main:system/core/init/service.cpp;l=587). it forks, drops privileges in the child, then execs the binary.

> because linux dont have syscall to create direcly a process so to do that action you need to fork() then execve() =)), posix_spawn() is a wrapper for that fork and execve action too :D.

```cpp
Result<void> Service::Start() {                  // service.cpp:587
    ...
    socket.Create(scon);                         // :661
    pid_t pid = fork();                          // :688
    if (pid == 0) {
        // in the child, through RunService(), set the privi as declare in *.rc file
        setgid(attr.gid);                        // service_utils.cpp:295
        setgroups(attr.supp_gids...);            //                  :299
        setuid(attr.uid());                      //                  :303
        setexeccon(seclabel_);                   // service.cpp:244
        execv(args_[0], ...);                    // service.cpp:117, it got started here
    }
}
```

so this block

```sh
service tombstoned /system/bin/tombstoned       # tombstoned.rc
    user tombstoned
    group system
    socket tombstoned_crash seqpacket 0666 system system
```

`user tombstoned`, `group system` becomes `setuid(tombstoned)`, `setgid(system)` in the child.

```console
ming@lazy:~ $ adb shell ps -AZ | grep -i tombstone
u:r:tombstoned:s0              tombstoned     825     1   10775344   2848 0                   0 S tombstoned
```

| column | value | meaning |
|---|---|---|
| label | `u:r:tombstoned:s0` | selinux domain |
| user | `tombstoned` | uid, from the `.rc` file |
| pid | `825` | |
| ppid | `1` | init forked it |

`socket tombstoned_crash seqpacket 0666 system system` becomes `socket()` + `bind("/dev/socket/tombstoned_crash")` + `chmod(0666)` + `chown(system, system)`, and then the open fd is handed to the child in an environment variable `ANDROID_SOCKET_tombstoned_crash=3`. the daemon does not create it, it just reads the number back with `android_get_control_socket("tombstoned_crash")`.

example usage, in tombstoned itself:

```cpp
// system/core/debuggerd/tombstoned/tombstoned.cpp:504
int crash_socket = android_get_control_socket(kTombstonedCrashSocketName);
if (crash_socket == -1) {
    PLOG(FATAL) << "failed to get socket from init";
}
```

that call `android_get_control_socket()` is just `getenv("ANDROID_SOCKET_tombstoned_crash")` and `atoi()`. no `socket()`, no `bind()` the fd is already open and already bound and created.

one thing to notice: the socket is created at [`:661`](https://cs.android.com/android/platform/superproject/main/+/main:system/core/init/service.cpp;l=661), **before** the fork, while init is still root. that is how a process running as uid `tombstoned` can own a socket that belongs to `system:system`, because it never have created that itself.

=> socket is the common way to comunication with this kind of service so we can checking rc file to know can we reach that surface by checking uid gid. 

here you can see the socket have been created in real Samsung Galaxy S26

```console
ming@lazy:~ $ adb shell cat /proc/net/unix | grep -i tombstoned_crash
0000000000000000: 00000002 00000000 00010000 0005 01 26663 /dev/socket/tombstoned_crash
```

| field | value | meaning |
|---|---|---|
| RefCount | `00000002` | |
| Flags | `00010000` | `SO_ACCEPTCON`, the socket is in `listen()` |
| Type | `0005` | `SOCK_SEQPACKET` — the `seqpacket` written in the `.rc` file |
| St | `01` | no connection open yet |
| Inode | `26663` | |

next chapter we will discover the first attack surface is Init Service.
