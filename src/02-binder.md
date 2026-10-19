# Binder (IPC)

google also has documentation about this, you can read it here: https://source.android.com/docs/core/architecture/ipc/binder-overview

## my explain

i can briefly explain binder by my own understanding like this:

binder is a kernel driver created for communication between processes on android. normally on linux desktop they use unix domain socket, but android needs something similar to that but optimized for android, so they created Binder.

binder provides the features from the kernel side, mostly transferring data between processes, to create a seamless function call. like process A is calling a function of process B, but it looks like it is calling a function that belongs to itself.

> note: dont miss this part. binder provides the features to create a seamless function call, it doesnt make the call itself. that job drop to AIDL, who will use binder to do it.

fun fact: on android some system services still use unix domain socket, but far less than the one using binder through AIDL, you also will see me make explain about this in [chapter 5](05-attack_surface-init-service.md)

from google doc:
> In binder terms, the calling process is considered the client and its endpoint is called the binder proxy or proxy. Conversely, the process being called is the server and its endpoint is called the binder node or node.

Binder (IPC : inter-process communication) just provides the tools to do seamless function calling between processes. the one using those tools is called AIDL (Android Interface Definition Language), we will continue with it in [the next chapter](03-init-service-part1-aidl.md).

## random knowlege 
yea maybe drop into kernel source code to learn how it work under the hood is fun, but currently have a lot of things want to learn :D, so may be i will do details Binder analysis later the infomation above is enogh for you to learning next step and i will drop here some random knowlege about binder you can reading it for fun

### where is the binder ?
binder live in it own file system

```console
ming@lazy:~ $ adb shell mount | grep -i binder
binder on /dev/binderfs type binder (rw,relatime,max=1048576,stats=global)

ming@lazy:~ $ adb shell ls -l /dev/binderfs/
crw-rw-rw- 1 root root 506,   1 2026-10-05 12:18 binder
crw------- 1 root root 506,   0 2026-10-05 12:18 binder-control
drwxr-xr-x 3 root root        0 2026-10-05 12:18 binder_logs
drwxr-xr-x 2 root root        0 2026-10-05 12:18 features
crw-rw-rw- 1 root root 506,   2 2026-10-05 12:18 hwbinder
crw-rw-rw- 1 root root 506,   3 2026-10-05 12:18 vndbinder
```

```text
binder       apps and framework talk here
hwbinder     the Hardware abstraction layer (HAL)
vndbinder    vendor process to vendor process
```

`/dev/binder` is only a symlink into that folder, `binder_logs` is the kernel counters, you can read them without root.

```console
ming@lazy:~ $ adb shell head -6 /dev/binderfs/binder_logs/stats
binder stats:
BC_TRANSACTION: 3876840
BC_REPLY: 2133193
BC_FREE_BUFFER: 6004917
BC_INCREFS: 300004
BC_ACQUIRE: 300162
```

thats 4 million transactions since boot, my phone have just boot up for several hours.

### what binder can carry

Binder focus on transfering data 

```text
byte               your arguments and return value
fd                 you can hand your fd to other process, to using the other process should have right selinux privi
object reference   let you call an object living in another process
caller identity    using most from server side to verify the caller if needed
```

unix socket only have the first two


