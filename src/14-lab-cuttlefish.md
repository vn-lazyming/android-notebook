# Lab: booting an Android with Cuttlefish

this lab guides you through the process of emulating an android on your local machine using
cuttlefish. im currently using a fedora (linux) machine, so maybe the tutorial is the same for
other linux distributions.

## Android Virtual Device (AVD)

Android Emulator runs the Android operating system in a virtual machine called an Android
Virtual Device (AVD). Each AVD contains the full Android software stack.

you can check the documentation. simply we can say that AVD is a virtual phone with no android
installed yet, but it provides all the hardware emulation etc, so we could install android in
it and boot a running android system.

[AVD architecture — source.android.com](https://source.android.com/docs/setup/test/avd#architecture)

## Cuttlefish

similar to AVD but with some differences.

google confirms that
([source](https://source.android.com/docs/devices/cuttlefish#android-emulator)):

> The Android Emulator has been built around the use case of making app development easy, and
> it contains many functional hooks to appeal to the use cases of the Android app developer.
> This can present challenges if you want to build an emulator with your customized Android
> framework. If you need a virtual device that is representative of your custom platform or
> framework code or tip-of-tree Android, then Cuttlefish is an ideal virtual option.
> Cuttlefish is the canonical device for representing the current state of AOSP development.

we can understand it simply as: cuttlefish is trying to emulate the whole hardware that a real
phone needs to run the android framework, and it is mostly used for custom android framework —
that is what we need for some chapters in this book. for application development we can use
AVD, but for framework development we need cuttlefish.

## launch AOSP with cuttlefish

here is the official tutorial of google for launching aosp with cuttlefish:
[Cuttlefish — get started](https://source.android.com/docs/devices/cuttlefish/get-started)

## here is my simple tutorial using docker for all linux distribution

the official tutorial uses `apt` and `dpkg`, so only debian works. the official docker image
already has `cuttlefish-base`, `cuttlefish-user` and `cuttlefish-orchestration` installed, so
with docker it works on any distro.

you need docker installed, and your user in the `kvm` and `docker` groups.

### what is needed

- virtualisation, it comes from the host kernel
- the android itself, the guest images
- the host tools that boot it

the host kernel gives the device nodes, a container cannot fake these.

```console
$ ls -l /dev/kvm /dev/vhost-vsock /dev/vhost-net /dev/net/tun
crw-rw-rw-. 1 root kvm  10, 232 /dev/kvm
crw-rw-rw-. 1 root kvm  10, 241 /dev/vhost-vsock
crw-rw-rw-. 1 root kvm  10, 238 /dev/vhost-net
crw-rw-rw-. 1 root root 10, 200 /dev/net/tun
```

nonzero means your cpu can do virtualisation.

```console
$ grep -c -w -E 'vmx|svm' /proc/cpuinfo
32
```

### download

get two files from [ci.android.com](https://ci.android.com), branch `aosp-android-latest-release`,
target `aosp_cf_x86_64_only_phone`, variant `userdebug`, in the Artifacts panel:

- `aosp_cf_x86_64_only_phone-img-16373615.zip` (1.1G), the android: `super.img`, `boot.img`,
  `vbmeta.img`
- `cvd-host_package.tar.gz` (858M), the tools that boot it: `crosvm`, `launch_cvd`, `adb`

both must come from the same build id.

this prints the current good build id, so you dont have to click around the website.

```console
$ curl -s "https://ci.android.com/builds/branches/aosp-android-latest-release/status.json"
..."name":"aosp_cf_x86_64_only_phone-userdebug","last_known_good_build":"16373615"...
```

put both downloads in one folder and unpack them there, the tools look for the images next to
them.

```bash
mkdir android_lab && cd android_lab
tar -xf cvd-host_package.tar.gz
unzip aosp_cf_x86_64_only_phone-img-16373615.zip
```

### magic files

google ships no compose file, so i wrote these two. this is `docker-compose.yml`, put it in
the folder.

```yaml
services:
  cuttlefish:
    container_name: cflab
    image: us-docker.pkg.dev/android-cuttlefish-artifacts/cuttlefish-orchestration/cuttlefish-orchestration:stable

    # autostart.sh runs the image's run_services.sh then launch_cvd. replacing
    # this with sleep infinity loses the cvd-ebr bridge and crosvm fails on tap
    entrypoint: ["/cf/autostart.sh"]

    # needed to open /dev/kvm
    privileged: true

    # docker defaults to 1024, crosvm panics with "Too many open files"
    ulimits:
      nofile:
        soft: 524288
        hard: 524288

    # host kernel, a container cannot fake these
    devices:
      - /dev/kvm
      - /dev/vhost-vsock
      - /dev/vhost-net
      - /dev/net/tun

    volumes:
      - .:/cf
    working_dir: /cf

    # ports come from EXPOSE in the image's Containerfile, not 8443
    ports:
      - "127.0.0.1:1443:1443"                # ui
      - "127.0.0.1:2443:2443"                # host orchestrator
      - "127.0.0.1:6520:6520"                # adb
      - "127.0.0.1:15550-15560:15550-15560"  # webrtc media
```

this is `autostart.sh`, also in the folder, it needs `chmod +x` because docker runs it as the
entrypoint.

```bash
#!/bin/bash
set -u

# run_services.sh ends in tail -f, so it has to go to the background
/root/run_services.sh &

# wait for the bridge, otherwise crosvm cannot write to the tap device
for i in $(seq 1 30); do
    ip link show cvd-ebr >/dev/null 2>&1 && break
    sleep 1
done

cd /cf

# -report_anonymous_usage_stats=n so it does not ask Y/n without a tty
HOME=/cf ./bin/launch_cvd --daemon -report_anonymous_usage_stats=n

wait
```

### run it

one command, it pulls the image the first time and boots the device.

```bash
docker compose up -d
```

after about a minute, connect from the host machine, not from inside the container.

```bash
adb connect localhost:6520
```

to stop it.

```bash
docker compose down
```

the ui is at `https://localhost:1443`, the cert is self-signed so the browser will complain.

### what you get

```console
$ adb -s localhost:6520 shell 'getprop ro.product.model; getprop ro.build.type; getprop ro.build.version.release; getprop sys.boot_completed'
Cuttlefish x86_64 phone 64-bit only
userdebug
17
1
```
also you your adb have root privi too

## references

- [Cuttlefish — get started](https://source.android.com/docs/devices/cuttlefish/get-started)
- [Run Cuttlefish on an on-premise server](https://source.android.com/docs/devices/cuttlefish/on-premises)
- [google/android-cuttlefish](https://github.com/google/android-cuttlefish)
- [container/README.md](https://github.com/google/android-cuttlefish/blob/main/container/README.md)
