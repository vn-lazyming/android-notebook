# SELinux

i think this way its more easy to understand i will explain in simple how Selinux work first
then we go deep later

1. every **process** carries a type.
2. every **thing** it might touch — a file, a socket, a binder name, a property — carries a
type too.
3. there is one big list of which type may do what to which type. not on the list means denied.

## example
a policy rule comes in the form

```text
allow source target:class permissions;
```

where:

- **source** — the type (or attribute) of the subject of the rule. who is requesting the access?
- **target** — the type (or attribute) of the object. to what is the access requested?
- **class** — the kind of object (for example, file, socket) being accessed
- **permissions** — the operation (or set of operations) (for example, read, write) being
  performed. which ones are available depends on the class

an example of a rule is:

```text
allow untrusted_app app_data_file:file { read write };
```

this says that `untrusted_app` is allowed to read and write files labelled with the
`app_data_file` type.

## attribute

there are many types that are almost the same. `untrusted_app` is an app, but so is
`isolated_app`, and `priv_app`, and `system_app`. writing the same rule once for each of them
would be a mess.

so a type can be tagged with an **attribute**, which is just a group name. on my Samsung Galaxy
S26, all the app types are grouped into `appdomain`:

```text
(typeattributeset appdomain (
    adservices          bluetooth           device_as_webcam    ephemeral_app
    gmscore_app         isolated_app        isolated_compute_app mediaprovider
    mediaprovider_app   network_stack       nfc                 permissioncontroller_app
    platform_app        priv_app            radio               rkpdapp
    runas_app           sdk_sandbox_34      sdk_sandbox_audit   sdk_sandbox_next
    secure_element      shared_relro        shell               simpleperf
    system_app          traceur_app         untrusted_app       untrusted_app_25
    untrusted_app_27    untrusted_app_29    untrusted_app_30    untrusted_app_32
    vmlauncher_app      vzwomatrigger_app ))
```

34 of them. samsung adds 9 more of their own in `/vendor/etc/selinux/vendor_sepolicy.cil`:

```text
(typeattributeset appdomain (
    attiqi_app_202504   dsms_app_202504     mobicore_app        policyloader_app
    vendor_ims_app      vendor_sqe_app      vendor_test_app     vendor_wlbt_app
    vendor_telephony_silentlogging_app ))
```

now one rule covers all of them at once:

```text
(allow appdomain tombstoned (unix_stream_socket (connectto)))
```

that single line is what lets any app talk to `tombstoned`. no rule mentions `untrusted_app`
anywhere.

## macros

there are also some predefined macros that make writing a policy easier. for example:

```text
allow appdomain app_data_file:file rw_file_perms;
```

you can find their definitions in [public/global_macros](https://android.googlesource.com/platform/system/sepolicy/+/refs/heads/android17-release/public/global_macros):

```text
define(`rw_file_perms', `{ r_file_perms w_file_perms }')
```

which is itself built from two more:

```text
define(`r_file_perms', `{ getattr open read ioctl lock map watch watch_reads }')
define(`w_file_perms', `{ open append write lock map }')
```

## real world explore hehe
okay finishing with the boring lecture lets handons and explore selinux on Samsung Galaxy S26:

### .te and CIL

the same rule is written two ways depending on where you are reading it.

`.te` is what a human writes in the AOSP source tree:

```text
allow untrusted_app app_data_file:file { read write };
```

CIL is what the compiler turns it into, and it is the only form that ships on the phone:

```text
(allow untrusted_app app_data_file (file (read write)))
```

so you read `.te` in `system/sepolicy/`, and you grep CIL in `/system/etc/selinux/*.cil`.

### reading a real context

the `-Z` option shows the SELinux context of every process:

```console
ming@lazy:~ $ adb shell ps -AZ | tail
u:r:untrusted_app:s0:c96,c257,c512,c768 u0_a352 31710 1060 19790108 313460 0                  0 S org.telegram.messenger
u:r:gmscore_app:s0:c512,c768   u0_a276      31865  1060   17735032 147652 0                   0 S com.google.android.gms.unstable
u:r:shell:s0                   shell        31906  3136   10843416   3752 unix_stream_read_generic 0 S abb
u:r:system_app:s0              system       32146  1060   17132616  81500 0                   0 S com.samsung.sait.sohservice
u:r:untrusted_app:s0:c39,c257,c512,c768 u0_a295 32267 1060 19270040 114032 0                  0 S com.google.android.apps.maps
u:r:mediaprovider:s0:c512,c768 u0_a75       32302  1060   17248384  90728 0                   0 S android.process.media
u:r:kernel:s0                  root         32482     2          0      0 0                   0 I [kworker/9:1-events]
u:r:priv_app:s0:c512,c768      u0_a269      32568  1060   17186532  89948 0                   0 S com.google.android.projection.gearhead:shared
u:r:priv_app:s0:c512,c768      u0_a269      32592  1060   17047540  82188 0                   0 S com.google.android.projection.gearhead:car
u:r:priv_app:s0:c512,c768      u0_a269      32627  1060   17108636  85464 0                   0 S com.google.android.projection.gearhead:projection
ming@lazy:~ $
```

take one normal app out of that list, telegram:

```text
u:r:untrusted_app:s0:c96,c257,c512,c768 u0_a352 31710 1060 19790108 313460 0                  0 S org.telegram.messenger
```

the context part is this:

```text
u:r:untrusted_app:s0:c96,c257,c512,c768
```

that looks more complicated than what we learned, but it is normal. google explains the extra
fields under [security contexts](https://source.android.com/docs/security/features/selinux/concepts#security_contexts):

> When debugging SELinux policies or labelling files (using file_contexts or ls -Z), you might
> come across a security context (also known as a label). For example:
> u:r:untrusted_app:s0:c15,c256,c513,c768. A security context has the format:
> user:role:type:sensitivity[:categories]. You can usually ignore the user, role and
> sensitivity fields of a context (see Specificity). The type field is explained in the
> previous section. categories are part of the Multi-Level Security (MLS) support in SELinux.
> In Android 12 and higher, categories are used to:
>
> - Isolate the app data from access by another app,
> - Isolate the app data from one physical user to another.

the reason is simple. SELinux has far more functionality than a phone needs, so android only
uses part of it.

out of the full format

```text
user:role:type:sensitivity[:categories]
```

only two fields carry any information:

```text
u : r : untrusted_app : s0 : c96,c257,c512,c768
        ^^^^^^^^^^^^^        ^^^^^^^^^^^^^^^^^^
        the type             the categories
```

you can ignore the categories too its does not matter when we explore surface. they are
generated automatically from the app's uid, and their only job is the one google states keeping
one app's data away from another, and one physical user's away from another.

### what type is this object ?

#### ask the phone with -Z

assume you want to check the type of one file, just ask the phone with `ls -Z`:

```console
ming@lazy:~ $ adb shell ls -Z /system/build.prop
u:object_r:system_file:s0        /system/build.prop
```

so the type is `system_file`

but we also have `getprop -Z`, and `ps -Z` 

#### the *_contexts files

but when in case you cant using -Z like `System Service` or you even dont have the phone you
can using the `*_contexts` file

here is some context file in Galaxy S26

```console
ming@lazy:~ $ adb shell ls -1 /system/etc/selinux/
plat_file_contexts
plat_hwservice_contexts
plat_keystore2_key_contexts
plat_property_contexts
plat_seapp_contexts
plat_service_contexts
plat_tee_service_contexts
...
```

one file per kind of object:

- `file_contexts` — paths, the same thing With `ls -Z` 
- `service_contexts` — binder services, what `service list` shows
- `hwservice_contexts` — the old HIDL services
- `vndservice_contexts` — vendor binder, on `/vendor` only
- `property_contexts` — properties, what `getprop -Z` would tell you
- `seapp_contexts` — apps, which domain a package runs in
- `keystore2_key_contexts`, `tee_service_contexts` — keys and trustlet services

> note each one of these files has its own way of being written. google picks the format per
> kind of object, because the things being labelled are not same a path is not a service
> name, and an app is not a file. so there is no single syntax to learn, there are several.
>
> `file_contexts` keys are **regex**:
>
> ```text
> /init\..*           u:object_r:rootfs:s0
> /res(/.*)?          u:object_r:rootfs:s0
> ```
>
> `service_contexts` keys are **exact names**, with a `*` at the bottom catching the rest:
>
> ```text
> android.frameworks.cameraservice.service.ICameraService/default   u:object_r:fwk_camera_service:s0
> *                                                                 u:object_r:default_android_service:s0
> ```
>
> and `seapp_contexts` is conditions on the left and
> outputs on the right:
>
> ```text
> user=_app seinfo=platform name=com.android.traceur domain=traceur_app type=app_data_file levelFrom=all
> ```
>
> the documentation for these is the comment header of the file in the aosp source, for example
> [private/seapp_contexts](https://android.googlesource.com/platform/system/sepolicy/+/refs/heads/main/private/seapp_contexts).

so take a name from `service list`:

```console
ming@lazy:~ $ adb shell service list | grep -w clipboard
146	clipboard: [android.content.IClipboard]
345	semclipboard: [android.sec.clipboard.IClipboardService]
```

and look for it.

```console
ming@lazy:~ $ adb shell "grep -rn '^clipboard ' /*/etc/selinux/*_service_contexts"
grep: /odm/etc/selinux/odm_service_contexts: Bad file descriptor
/system/etc/selinux/plat_service_contexts:219:clipboard                                 u:object_r:clipboard_service:s0
grep: /vendor/etc/selinux/vendor_service_contexts: Bad file descriptor
```

so the type of `clipboard` service is `clipboard_service` 

same command for `semclipboard`

```console
ming@lazy:~ $ adb shell "grep -rn '^semclipboard' /*/etc/selinux/*_service_contexts"
grep: /odm/etc/selinux/odm_service_contexts: Bad file descriptor
/system_ext/etc/selinux/system_ext_service_contexts:196:semclipboard                                u:object_r:semclipboard_service:s0
grep: /vendor/etc/selinux/vendor_service_contexts: Bad file descriptor
```

the result in `system_ext` because this create by vendor(samsung) they create a folder to
distinguish. and the type we got is `semclipboard_service`


#### when the phone wont give you the file

now the second case, the one where you cant read the file at all. some context files are
blocked by default, and that is fine because you can get them from the official firmware
download anyway.

there are 34 context files on my phone, and `shell` cannot read 6 of them:

```console
ming@lazy:~ $ adb shell head -c1 /vendor/etc/selinux/vendor_service_contexts
head: /vendor/etc/selinux/vendor_service_contexts: Permission denied
```

with a samsung Galaxy S26 we can download the firmware using
[samloader](https://github.com/samloader/samloader):

```console
$ ./samloader download -m SM-S942B -r XXV -j 16 -d . --verbose
```

that gives one big zip. the partitions live in `super.raw.img` inside it, and each one is an
EROFS image:

```console
$ file parts/odm_a.img
EROFS filesystem, compat: SB_CHKSUM MTIME, blocksize=12, uuid=6E9170B5-...
```

to extract that you need `erofs-utils` installed first:

```console
$ sudo dnf install erofs-utils
```

one image is one partition, so extract all five:

```console
$ for p in system system_ext product vendor odm; do
      fsck.erofs --extract=./out/$p parts/${p}_a.img
  done
$ find ./out -name '*_contexts' | wc -l
34
```

that is all 34, including the 6 the phone would not give you.

> note with context files we dont have a tool like `sesearch`, they are plain text so grep is enough

### how to use all the files and tools to gather information?

#### where the policy comes from

read chapter 01 first to know about the init binary.

in [system/core/init/main.cpp:73](https://cs.android.com/android/platform/superproject/+/android-latest-release:system/core/init/main.cpp;drc=0ae463de7990a66d7dc591caacb4b943768d7c41;l=73)

this is the function used to setup SELinux in Android right after the linux kernel finished booting
```c
    if (!strcmp(argv[1], "selinux_setup")) {
        return SetupSelinux(argv);
    }
```
follow the call trace

```text
SetupSelinux(argv)            <- system/core/init/main.cpp:73
  LoadSelinuxPolicyAndroid()
    ReadPolicy(&policy)
      IsSplitPolicyDevice()
```

in [system/core/init/selinux.cpp:226](https://cs.android.com/android/platform/superproject/main/+/main:system/core/init/selinux.cpp;drc=61197364367c9e404c7da6900658f1b16c42d0da;l=226)
```cpp
bool OpenSplitPolicy(PolicyFile* policy_file) {
    ...
    // fast path: is there already a compiled policy shipped on /vendor or /odm?
    if (auto res = FindPrecompiledSplitPolicy(); res.ok()) {
        unique_fd fd(open(res->c_str(), O_RDONLY | O_CLOEXEC | O_BINARY));
        policy_file->fd = std::move(fd);
        return true;                       // done, nothing to compile
    }

    LOG(INFO) << "Compiling SELinux policy";

    // the output goes to /dev, the only tmpfs available this early
    char compiled_sepolicy[] = "/dev/sepolicy.XXXXXX";
    unique_fd compiled_sepolicy_fd(mkostemp(compiled_sepolicy, O_CLOEXEC));

    // two files are mandatory
    std::string vendor_policy_cil_file("/vendor/etc/selinux/vendor_sepolicy.cil");
    if (access(vendor_policy_cil_file.c_str(), F_OK) == -1) return false;

    std::string plat_pub_versioned_cil_file("/vendor/etc/selinux/plat_pub_versioned.cil");
    if (access(plat_pub_versioned_cil_file.c_str(), F_OK) == -1) return false;

    // the rest are optional: check if the file is there, drop it if not
    std::string system_ext_policy_cil_file("/system_ext/etc/selinux/system_ext_sepolicy.cil");
    if (access(system_ext_policy_cil_file.c_str(), F_OK) == -1) {
        system_ext_policy_cil_file.clear();
    }
    ...                                    // same pattern for product, odm, mapping, genfs

    std::vector<const char*> compile_args {
        "/system/bin/secilc",              // the compiler
        plat_policy_cil_file,
        "-m", "-M", "true", "-G", "-N",
        "-c", version_as_string.c_str(),
        plat_mapping_file.c_str(),
        "-o", compiled_sepolicy,           // where to write the binary policy
        "-f", "/sys/fs/selinux/null",
    };

    // append every optional file that turned out to exist
    if (!system_ext_policy_cil_file.empty()) {
        compile_args.push_back(system_ext_policy_cil_file.c_str());
    }
    ...
    compile_args.push_back(vendor_policy_cil_file.c_str());
    compile_args.push_back(nullptr);

    ForkExecveAndWaitForCompletion(compile_args[0], (char**)compile_args.data());

    unlink(compiled_sepolicy);             // drop the name, keep the fd
    policy_file->fd = std::move(compiled_sepolicy_fd);
    return true;
}
```

so all the .cil policy files need to be selected and compiled into one binary before the kernel
can load it. that binary contains all the selinux info you need when you analyze the surface.

#### asking the policy with sesearch

if you get that binary you can use `sesearch` to answer some questions

assume s26.policy is the binary. this cli answers what untrusted_app can do:
```console
sesearch --allow -s untrusted_app s26.policy
```

or what socket untrusted_app can connect to:
```console
sesearch --allow -s untrusted_app -c unix_stream_socket -p connectto s26.policy
```
there is a lot of ways to use sesearch to answer your questions when you explore the surface.

#### getting the binary off the phone

here is how to get the binary, demonstrated on a Samsung Galaxy S26
```console
ming@lazy:~ $ adb pull /sys/fs/selinux/policy
/sys/fs/selinux/policy: 1 file pulled, 0 skipped. 28.0 MB/s (1575215 bytes in 0.054s)
```

funny thing, if you try to cat it you wont get it =))
```console
ming@lazy:~ $ adb shell cat /sys/fs/selinux/policy
cat: /sys/fs/selinux/policy: Permission denied
```
this is all because `adb shell` and `adb pull` running in different selinux domain.

#### building it yourself from the .cil files

if you cant get that binary you can build it yourself from all the .cil files you have, using
`secilc` the same way `OpenSplitPolicy()` does in the android source.


here is all the .cil file ignore the old mapping .cil file in Samsung Galaxy S26, this is world
readable and can pull using adb, pull it and you can compile the binary yourself
```console
ming@lazy:~ $ adb shell 'ls -l /*/etc/selinux/*.cil /*/etc/selinux/mapping/$(getprop ro.board.api_level).cil 2>/dev/null'
-rw-r--r-- 1 root root       1 2022-01-01 07:00 /odm/etc/selinux/odm_sepolicy.cil
-rw-r--r-- 1 root root       1 2022-01-01 07:00 /product/etc/selinux/mapping/202504.cil
-rw-r--r-- 1 root root       1 2022-01-01 07:00 /product/etc/selinux/product_sepolicy.cil
-rw-r--r-- 1 root root  229237 2022-01-01 07:00 /system/etc/selinux/mapping/202504.cil
-rw-r--r-- 1 root root 3006771 2022-01-01 07:00 /system/etc/selinux/plat_sepolicy.cil
-rw-r--r-- 1 root root     142 2022-01-01 07:00 /system/etc/selinux/plat_sepolicy_genfs_202504.cil
-rw-r--r-- 1 root root     463 2022-01-01 07:00 /system/etc/selinux/plat_sepolicy_genfs_202604.cil
-rw-r--r-- 1 root root   89895 2022-01-01 07:00 /system_ext/etc/selinux/mapping/202504.cil
-rw-r--r-- 1 root root  595926 2022-01-01 07:00 /system_ext/etc/selinux/system_ext_sepolicy.cil
-rw-r--r-- 1 root root  482456 2022-01-01 07:00 /vendor/etc/selinux/plat_pub_versioned.cil
-rw-r--r-- 1 root root 1835211 2022-01-01 07:00 /vendor/etc/selinux/vendor_sepolicy.cil
```

## practice: finding what domain does an app run in ?

### on the phone

```console
ming@lazy:~ $ adb shell ps -AZ -o label,user,pid,cmd | grep aasa
u:r:aasa_service_app:s0:c512,c768  system  16792  ung.aasaservice
```

so it runs as `aasa_service_app`, and the unix user is `system`. 
### another way to do

seinfo plus the package name gives the domain

greping in `seapp_contexts`also give you the answer for selinux type:

```console
ming@lazy:~ $ adb shell "grep -rn aasaservice /*/etc/selinux/*_seapp_contexts"
/system_ext/etc/selinux/system_ext_seapp_contexts:27:user=system seinfo=platform name=com.samsung.aasaservice domain=aasa_service_app type=aasa_service_app_data_file levelFrom=user
```

the same grep works on the files you extracted from the firmware, no phone needed:

```console
$ grep -rn aasaservice out/*/etc/selinux/*_seapp_contexts
out/system_ext/etc/selinux/system_ext_seapp_contexts:27:user=system seinfo=platform name=com.samsung.aasaservice domain=aasa_service_app type=aasa_service_app_data_file levelFrom=user
```

base on the google documentation for the seapp_contexts file, which is the comment header of
[private/seapp_contexts](https://android.googlesource.com/platform/system/sepolicy/+/refs/heads/main/private/seapp_contexts)
in the aosp source:

> All specified input selectors in an entry must match (i.e. logical AND).
>
> `domain=` determines the label to be used for the app process; entries without `domain=` are
> ignored for this purpose.
>
> `type=` specifies the label to be used for the app data directory; entries without `type=` are
> ignored for this purpose.

the left side is conditions you can ignore it, and the right side as the result:

- `domain=aasa_service_app` — is the selinux type of process com.samsung.aasaservice 

so `domain=aasa_service_app`. that is the same type as `ps -Z` gave us at the
start

## references

- [SELinux concepts — Android Open Source Project](https://source.android.com/docs/security/features/selinux/concepts)
