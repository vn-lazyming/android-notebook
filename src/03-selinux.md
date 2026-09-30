# SELinux

i think this way its more easy to understand i will explain in simple how Selinux work first then we go deep later

1. every **process** carries a type.
2. every **thing** it might touch — a file, a socket, a binder name, a property — carries a type too.
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
- **permissions** — the operation (or set of operations) (for example, read, write) being performed. which ones are available depends on the class

an example of a rule is:

```text
allow untrusted_app app_data_file:file { read write };
```

this says that `untrusted_app` is allowed to read and write files labelled with the `app_data_file` type.

### attribute

there are many types that are almost the same. `untrusted_app` is an app, but so is `isolated_app`, and `priv_app`, and `system_app`. writing the same rule once for each of them would be a mess.

so a type can be tagged with an **attribute**, which is just a group name. on my Samsung Galaxy S26, all the app types are grouped into `appdomain`:

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

that single line is what lets any app talk to `tombstoned`. no rule mentions `untrusted_app` anywhere.

### macros

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

that looks more complicated than what we learned, but it is normal. google explains the extra fields under [security contexts](https://source.android.com/docs/security/features/selinux/concepts#security_contexts):

> When debugging SELinux policies or labelling files (using file_contexts or ls -Z), you might come across a security context (also known as a label). For example: u:r:untrusted_app:s0:c15,c256,c513,c768. A security context has the format: user:role:type:sensitivity[:categories]. You can usually ignore the user, role and sensitivity fields of a context (see Specificity). The type field is explained in the previous section. categories are part of the Multi-Level Security (MLS) support in SELinux. In Android 12 and higher, categories are used to:
>
> - Isolate the app data from access by another app,
> - Isolate the app data from one physical user to another.

the reason is simple. SELinux has far more functionality than a phone needs, so android only uses part of it.

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

you can ignore the categories too its does not matter when we explore surface. they are generated automatically from the app's uid, and their only job is the one google states keeping one app's data away from another, and one physical user's away from another.

### what type is this object ?

assume you want to check the type of one file, just ask the phone with `ls -Z`:

```
ming@lazy:~ $ adb shell ls -Z /system/build.prop
u:object_r:system_file:s0        /system/build.prop
```

so the type is `system_file`

but we also have `getprop -Z`, and `ps -Z` 

but when in case you cant using -Z like `System Service` or you even dont have the phone

### how to use all the files and tools to gather information?

read chapter 01 first to know about the init binary.

in [system/core/init/main.cpp:73](https://cs.android.com/android/platform/superproject/+/android-latest-release:system/core/init/main.cpp;drc=0ae463de7990a66d7dc591caacb4b943768d7c41;l=73)

this is the function used to setup SELinux in Android right after the linux kernel finished booting
```c
    if (!strcmp(argv[1], "selinux_setup")) {
        return SetupSelinux(argv);
    }
```
follow the call trace

```
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

so all the .cil policy files need to be selected and compiled into one binary before the kernel can load it. that binary contains all the selinux info you need when you analyze the surface.

if you get that binary you can use `sesearch` to answer some questions

assume s26.policy is the binary. this cli answers what untrusted_app can do:
```
sesearch --allow -s untrusted_app s26.policy
```

or what socket untrusted_app can connect to:
```
sesearch --allow -s untrusted_app -c unix_stream_socket -p connectto s26.policy
```
there is a lot of ways to use sesearch to answer your questions when you explore the surface.

here is how to get the binary, demonstrated on a Samsung Galaxy S26
```
ming@lazy:~ $ adb pull /sys/fs/selinux/policy
/sys/fs/selinux/policy: 1 file pulled, 0 skipped. 28.0 MB/s (1575215 bytes in 0.054s)
```

funny thing, if you try to cat it you wont get it =))
```
ming@lazy:~ $ adb shell cat /sys/fs/selinux/policy
cat: /sys/fs/selinux/policy: Permission denied
```
this is all because `adb shell` and `adb pull` running in different selinux domain.

if you cant get that binary you can build it yourself from all the .cil files you have, using `secilc` the same way `OpenSplitPolicy()` does in the android source.


here is all the .cil file ignore the old mapping .cil file in Samsung Galaxy S26, this is world readable and can pull using adb, pull it and you can compile the binary yourself
```
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

## references

- [SELinux concepts — Android Open Source Project](https://source.android.com/docs/security/features/selinux/concepts)
