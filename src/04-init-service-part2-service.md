# Init service, part 2: the service

hii welcome back hope you are doing well. In this part, we will continue with the init service after part1 we have finish writing logic code and finish the AIDL part.


## service manager 

So in the [AIDL chapter](03-init-service-part1-aidl.md) we learned that to use AIDL, the client needs a proxy object, also called binder proxy (`BpCounter`). but who hands it to the client? how does it get one?

i think i will make a chapter about ServiceManager later, when i read its real code. for now i just have enough knowledge to explain how it works :D

### What does servicemanager do

servicemanager it self is Init service, which we are learning now, its job is simple: it is the **phonebook of binder**, it keeps a list of `name -> binder` in memory.

how can everyone find it ? when it starts, it tells the binder driver "i am the context manager". after that, handle `0` always points to servicemanager, so any process can talk to it without asking anybody.

it has two main jobs:

- `addService(name, binder)`: the server puts itself into the list
- `getService(name)`: the client asks by name, and gets the binder back

here is how both sides use them. server side, in our `counterd`:

first to adding our service to Service mananger
```cpp
// lab/init-service/counterd.cpp:52-62
// create our Counter object, this is the BnCounter (the node)
auto service = ::ndk::SharedRefBase::make<Counter>();

// the name that clients will search for
std::string name = std::string(Counter::descriptor) + "/default";

// put the node into servicemanager's list under that name
AServiceManager_addService(service->asBinder().get(), name.c_str());
```

when calling `addService`, servicemanager will create an object of type `BpBinder` to store a number called handle, kinda similar to an fd number. with an fd number we have `FILE*`, with binder we have `BpBinder` to store the handle number.

from [previous chapter](03-init-service-part1-aidl.md) we have learned what `BpCounter` is, and you might confuse it with `BpBinder`, so let me explain again:

- `BpCounter` knows **what** to send: it packs `setValue(3, 42)` into a parcel
- `BpBinder` knows **where** to send: it holds the handle that points to `counterd`

`BpCounter` holds a `BpBinder` inside. it packs the data, then gives it to `BpBinder` to send.

```text
client                                       counterd
──────                                       ────────
BpCounter   what to send
  │  setValue(3, 42) → parcel
  ▼
BpBinder    where to send (handle) ──► kernel ──► Counter::setValue(3, 42)
```

client side code demonstrate getting proxy to calling service through AIDL:

```cpp
// ask servicemanager (handle 0) by name, we get back a BpBinder
ndk::SpAIBinder binder(AServiceManager_waitForService("com.example.ICounter/default"));

// wrap the BpBinder into BpCounter, now it looks like a normal ICounter
std::shared_ptr<ICounter> counter = ICounter::fromBinder(binder);

// a normal function call, BpCounter packs it and sends it to counterd
counter->setValue(3, 42);
```

after that the client calls the service directly, servicemanager is not in the middle anymore.

## the main()
init service is like normal process they have main() function like other normal program. here is the full main version of couter service

```cpp
// lab/init-service/counterd.cpp:47-66
int main() {
  // threads are for RECEIVING. with no pool, nobody is parked in the ioctl
  ABinderProcess_setThreadPoolMaxThreadCount(4);
  ABinderProcess_startThreadPool();

  auto service = ::ndk::SharedRefBase::make<Counter>();

  // same shape as ILights/default on a real phone
  std::string name = std::string(Counter::descriptor) + "/default";

  if (AServiceManager_addService(service->asBinder().get(), name.c_str()) != STATUS_OK) {
    // usually selinux saying no, or the name missing from service_contexts
    __android_log_print(ANDROID_LOG_ERROR, TAG, "addService(%s) failed", name.c_str());
    return 1;
  }
  __android_log_print(ANDROID_LOG_INFO, TAG, "registered as %s", name.c_str());

  ABinderProcess_joinThreadPool();  // parks main too, never returns
  return 1;
}
```

the `addService` part we already know. the new thing here is the **thread pool**.

### thread pool

the kernel delivers `setValue` to counterd. but deliver to who ? a process can not receive by itself we can see no listen function in the mainfunction, so `libbinder` have function to create thread sit inside the binder driver and wait for work. that is the thread pool:


- `startThreadPool()` creates **one new thread**, it goes into the binder driver and waits
- `joinThreadPool()` does not create anything, it sends **`main` itself** to wait too. that is why it never returns, and the process never exits

so after `main()` we have 2 threads waiting for calls:

```text
counterd
 ├ main        ← joinThreadPool()
 └ thread #1   ← startThreadPool()
```

when a call comes, the kernel wakes one of them, it runs `onTransact` → your `Counter::setValue`, then goes back to wait. if both are busy, the kernel asks counterd to make one more thread, up to the 4 we set with `setThreadPoolMaxThreadCount(4)`.

and because several threads can run calls at the same time, two clients can call `setValue` together. that is why `Counter` has the `lock_` in part 1 :D

## build

```console
$ cd lab/init-service
$ ./build.sh
```

what `build.sh` does:

- runs aidl again, so `gen/` is fresh
- compiles `counterd.cpp` together with `gen/com/example/ICounter.cpp`. remember, both sides of the code live in `ICounter.cpp`, our server needs the `BnCounter` and `onTransact` part
- links against `libbinder_ndk.so` pulled from the device, because the NDK stub does not export `AServiceManager_*`

the NDK does not even ship `binder_manager.h` and `binder_process.h` (see `fetch-headers.sh`), so we take them from AOSP. `AServiceManager_*` and `ABinderProcess_*` are platform only APIs, normal apps are not supposed to register a service. init services are normally built inside AOSP, together with the whole android, by google or the vendor. so they can use the AOSP build system (Soong) with an `Android.bp` file instead of the NDK, and there the full `libbinder_ndk` is already available, no header collecting like us.

a real one from AOSP:

```text
// hardware/interfaces/authsecret/aidl/default/Android.bp
cc_binary {
    name: "android.hardware.authsecret-service.example",
    relative_install_path: "hw",
    vendor: true,
    srcs: [
        "service.cpp",
        "AuthSecret.cpp",
    ],
    shared_libs: [
        "libbinder_ndk",
        "liblog",
    ],
    static_libs: [
        "android.hardware.authsecret-V1-ndk",
        "libbase",
    ],
    stl: "c++_static",
}
```

- `libbinder_ndk` is the same library we pulled from the device
- `android.hardware.authsecret-V1-ndk` is the code aidl generates, like our `gen/`. the build system runs aidl for you
- other services also add `init_rc: [...]` here, so the `.rc` file gets installed together with the binary

we are not building the whole android, so `build.sh` does the same thing by hand.

## the .rc file

remember `tombstoned` in [chapter 1](01-init-and-rc-file.md) ? now we write our own:

```sh
# lab/init-service/counterd.rc
service counterd /system/bin/counterd
    interface aidl com.example.ICounter/default
    class main
    user system
    group system
```

- `service counterd /system/bin/counterd`: the name and the binary. init will fork + exec it like chapter 1
- `class main`: started at boot together with every other `class main` service
- `user system` / `group system`: becomes `setuid(system)` / `setgid(system)` in the child, same as chapter 1
- `interface aidl com.example.ICounter/default`: tells init "this service provides this name". init only stores it ([`ParseInterface()`](https://cs.android.com/android/platform/superproject/main/+/main:system/core/init/service_parser.cpp), service_parser.cpp:200)

why does init need to know the name ? for the case the service is **not running yet**:

```text
client: "give me com.example.ICounter/default"
servicemanager: "not in my list... hey init, who provides this name ?"
init: "counterd said it does, let me start it"
counterd: starts, addService(...)
servicemanager: "here you go"
```

so we can add `disabled` to the .rc, then counterd does not start at boot, it only starts the first time a client asks for it. that is called a **lazy service**. ours does not have `disabled`, so it just starts at boot like normal.

## selinux

> this part is write with help of claude, i realy want to wrote all this my self but i got a fever to day so hope you still love it

i highly recomend you to reading my [selinux chapter](08-selinux.md) first its perty good :D

if you just push the binary and the .rc and reboot, `addService` fails. servicemanager will check selinux before it accepts, so we need to adding selinux policy for our init service

**1. a domain for our process**

```lisp
(type counterd)
(type counterd_exec)
(typetransition init counterd_exec process counterd)
```

- `(type counterd)`: create a new label `counterd`, for the **process** when it runs
- `(type counterd_exec)`: create a new label `counterd_exec`, for the **file** `/system/bin/counterd` on disk
- `(typetransition init counterd_exec process counterd)`: read it like a sentence, when **init** runs a file labeled **counterd_exec**, the new **process** gets the label **counterd**

the file gets its label from one line in `file_contexts`:

```text
/system/bin/counterd       u:object_r:counterd_exec:s0
```

**2. a label for the service name**

```text
com.example.ICounter/default              u:object_r:counterd_service:s0
```

process has a label, file has a label, and the service name needs one too. this line goes in `service_contexts`, read it like a sentence: the service named **com.example.ICounter/default** gets the label **counterd_service**

servicemanager uses it every time someone calls `addService` or `getService`:

1. look up the name in `service_contexts` → `counterd_service`
2. ask selinux: can `counterd` do `add` on `counterd_service` ? (that is the rule in 3 below)
3. yes → accept, no → refuse

no line here = step 1 finds nothing = refused.

**3. allow us to add it**

```lisp
(allow counterd counterd_service (service_manager (add find)))
```

read it like a sentence: process **counterd** is allowed to **add** and **find** the service labeled **counterd_service**

this is the answer to step 2 above. without it, servicemanager asks selinux "can counterd add this ?" and the answer is no.

**4. allow binder between us and servicemanager**

```lisp
(allow counterd servicemanager (binder (call transfer)))
(allow servicemanager counterd (binder (call transfer)))
```

two rule above mean: process **counterd** is allowed to **call** servicemanager and **transfer** a binder object to it. the second line is the same, the other way around.

- `call`: send a transaction. `addService` is a call to servicemanager
- `transfer`: put a binder object inside the transaction. `addService` sends our `Counter`, so it needs this

3 is checked by servicemanager, 4 is checked by the kernel, when the transaction goes through binder.

in real AOSP you do not write all of this by hand, the comments in `counterd.cil` show the macros: `init_daemon_domain(counterd)` and `add_service(counterd, counterd_service)`. but you have to build the ASOP to using it.

## run it

one script does everything on [cuttlefish](10-lab-cuttlefish.md):

```console
$ ./setup-policy.sh
```

its mainly does 3 things:

- **copy** our files to the phone: the binary, the .rc, and the selinux lines from above
- **reboot**, because init only reads .rc and policy at boot
- **start** counterd

the comment at the top of `setup-policy.sh` explains every small step if you are curious.

```console
$ adb shell ps -AZ | grep counterd
u:r:counterd:s0                system        2549     1   10820412   5124 rust_binder_wait    0 S counterd
```

running in our domain `counterd`, as uid `system`, ppid `1` so init started it.

```console
$ adb shell service check com.example.ICounter/default
Service com.example.ICounter/default: found
```

servicemanager has our name in its list.

```console
$ adb logcat -d -s counterd
--------- beginning of main
10-19 11:57:43.495  2549  2549 I counterd: registered as com.example.ICounter/default
```

and our own log line, `addService` passed.


## last word

- servicemanager is the phonebook of binder, `name -> binder`. the server puts its service in with `addService`, and the client looks it up by name.
- the client gets a `BpBinder` that holds a handle, and `BpCounter` wraps it, so the client calls `setValue` like a normal function.
- the `.rc` file tells init how to start the service, and servicemanager can ask init to start it when nobody runs it yet.
- selinux has to allow the service name and the binder calls, or `addService` fails.

[next chapter](05-attack_surface-init-service.md) we look at counterd from the attacker side :D
