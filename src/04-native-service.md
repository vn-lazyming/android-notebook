<!-- # Native service attack surface

in the last chapter we saw `init` start processes at boot from a service block in a .rc file. those processes are what we call native services.

## how you talk to one

### with service using socket
#### DAC gate
some services declare a socket in their .rc file. that socket is how other processes reach them, so it is the first thing to look at.

```sh
socket tombstoned_crash seqpacket 0666 system system
       name             type      mode owner  group
```

the mode `0666` is the DAC part. the last digit is what every other process gets, and `6` means read and write, so as far as unix permissions go anyone can connect. the `system system` part does nothing while that digit is open.

but that is only the first gate.

#### SELinux gate

if you have not met SELinux before, read [our selinux chapter](12-selinux.md) first.

you can find the socket's label in `file_contexts`:

```console
ming@lazy:~ $ adb shell grep tombstoned /system/etc/selinux/plat_file_contexts
/dev/socket/tombstoned_crash       u:object_r:tombstoned_crash_socket:s0
/dev/socket/tombstoned_intercept   u:object_r:tombstoned_intercept_socket:s0
/dev/socket/tombstoned_java_trace  u:object_r:tombstoned_java_trace_socket:s0
```

three sockets from the same `.rc` file. same mode, same owner, same group — three different labels. the mode is identical for all three, so the mode is not what decides. an app may reach `tombstoned_crash`, because any app can crash. the same app may not reach `tombstoned_intercept`.

connecting needs two rules, because it touches two classes:

```text
sock_file : write                open /dev/socket/tombstoned_crash
unix_stream_socket : connectto   reach the process listening behind it
```

both gates have to say yes. `0666` with no policy rule is closed. `0600` with a policy rule is also closed, because DAC runs first. reading one of the two and stopping is how you decide something is reachable when it is not. -->



# Native service

in the last chapter we saw `init` start processes at boot from a service block in a `.rc` file. those processes are what we call native services.

how about trying to create one native service yourself? to learn. before that you should setup the lab from [the lab chapter](14-lab-cuttlefish.md) first, then come back to this chapter. or if you dont want hands on you can just read it and skip the lab. your choice

