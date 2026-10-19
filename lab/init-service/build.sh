#!/bin/bash
# builds counterd for the x86_64 cuttlefish device
set -eu

NDK=$HOME/Android/Sdk/ndk/30.0.16248370/toolchains/llvm/prebuilt/linux-x86_64/bin
AIDL=$HOME/Android/Sdk/build-tools/36.1.0/aidl

# the C++ helper headers aidl generates against, which no NDK ships. see fetch-headers.sh
[ -d aosp-headers ] || ./fetch-headers.sh

# .aidl -> C++, 4 files under gen/
rm -rf gen
"$AIDL" --lang=ndk -o gen -h gen/include -I . com/example/ICounter.aidl

# the NDK stub exports no AServiceManager_*, so link against the real one off the device
[ -f libbinder_ndk.so ] || adb pull /system/lib64/libbinder_ndk.so .

# android37 matches the device, so nothing about api levels needs patching
"$NDK/x86_64-linux-android37-clang++" -O2 -static-libstdc++ \
    -Iaosp-headers -Igen/include \
    counterd.cpp gen/com/example/ICounter.cpp \
    libbinder_ndk.so -llog \
    -o counterd

file counterd
