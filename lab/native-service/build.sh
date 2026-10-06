#!/bin/bash
# builds counterd for the x86_64 cuttlefish device
set -eu

NDK=$HOME/Android/Sdk/ndk/23.2.8568313/toolchains/llvm/prebuilt/linux-x86_64/bin
AIDL=$HOME/Android/Sdk/build-tools/36.1.0/aidl

# the binder headers aidl expects, see the comment in fetch-headers.sh
[ -d aosp-headers ] || ./fetch-headers.sh

# .aidl -> C++, 4 files under gen/
rm -rf gen
"$AIDL" --lang=ndk -o gen -h gen/include -I . com/example/ICounter.aidl

# the NDK stub exports 102 functions and none of them is AServiceManager_*,
# so we link against the real one off the device
[ -f libbinder_ndk.so ] || adb pull /system/lib64/libbinder_ndk.so .

# NDK 23 predates these two, and binder_manager.h names them
"$NDK/x86_64-linux-android31-clang++" -std=c++17 -O2 \
    -D__ANDROID_API_U__=34 -D__ANDROID_API_V__=35 \
    -static-libstdc++ \
    -Iaosp-headers -Igen/include \
    counterd.cpp gen/com/example/ICounter.cpp \
    libbinder_ndk.so -llog \
    -o counterd

file counterd
