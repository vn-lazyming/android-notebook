#!/bin/bash
# aidl --lang=ndk generates code that needs libbinder_ndk headers no NDK gives you.
#
#   NDK 30 ships only 5:  binder_ibinder.h binder_ibinder_jni.h binder_parcel.h
#                         binder_parcel_jni.h binder_status.h
#   it does NOT ship:     binder_parcel_utils.h binder_interface_utils.h
#                         binder_auto_utils.h binder_to_string.h binder_enums.h
#                         binder_parcelable_utils.h binder_internal_logging.h
#   and no NDK ever will: binder_manager.h binder_process.h
#                         (AServiceManager_* / ABinderProcess_*, include_platform only.
#                          see https://github.com/android/ndk/issues/1304)
#
# so take the set straight from AOSP, on the branch that matches the aidl we use.
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
