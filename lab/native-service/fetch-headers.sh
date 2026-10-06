#!/bin/bash
# NDK 23 ships android/binder_*.h, but too old for aidl 36: no AParcel_writeData,
# and ICInterface::defineClass takes 2 args instead of 4. so take the set from AOSP.
# AServiceManager_* and ABinderProcess_* are include_platform, never shipped in any NDK.
set -eu

B=https://android.googlesource.com/platform/frameworks/native/+/refs/heads/android16-release/libs/binder/ndk

mkdir -p aosp-headers/android
for p in \
    include_ndk/android/binder_parcel.h \
    include_ndk/android/binder_ibinder.h \
    include_ndk/android/binder_status.h \
    include_cpp/android/binder_parcel_utils.h \
    include_cpp/android/binder_interface_utils.h \
    include_cpp/android/binder_auto_utils.h \
    include_cpp/android/binder_to_string.h \
    include_cpp/android/binder_parcelable_utils.h \
    include_cpp/android/binder_internal_logging.h \
    include_platform/android/binder_manager.h \
    include_platform/android/binder_process.h
do
    curl -sf "$B/$p?format=TEXT" | base64 -d > "aosp-headers/android/$(basename "$p")"
done

ls -1 aosp-headers/android/
