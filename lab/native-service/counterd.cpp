// a native service that speaks AIDL, shaped like android.hardware.light.ILights
//   .aidl  -> com/example/ICounter.aidl
//   build  -> ./build.sh
//   init   -> counterd.rc

#include <aidl/com/example/BnCounter.h>
#include <android/binder_manager.h>
#include <android/binder_process.h>
#include <android/log.h>

#include <map>
#include <mutex>
#include <string>

using aidl::com::example::BnCounter;

namespace {

constexpr const char* kTag = "counterd";

class Counter : public BnCounter {
 public:
  // every binder call lands here, on a thread from the pool, not on main
  ::ndk::ScopedAStatus setValue(int32_t in_id, int32_t in_value) override {
    // the kernel stamps this, the caller cannot fake it
    const uid_t caller = AIBinder_getCallingUid();

    std::lock_guard<std::mutex> lock(mu_);
    values_[in_id] = in_value;

    __android_log_print(ANDROID_LOG_INFO, kTag, "setValue(%d, %d) from uid %u",
                        in_id, in_value, caller);
    return ::ndk::ScopedAStatus::ok();
  }

  ::ndk::ScopedAStatus getValues(std::vector<int32_t>* _aidl_return) override {
    std::lock_guard<std::mutex> lock(mu_);
    _aidl_return->clear();
    for (const auto& entry : values_) _aidl_return->push_back(entry.second);
    return ::ndk::ScopedAStatus::ok();
  }

 private:
  std::mutex mu_;                      // two binder threads can arrive at once
  std::map<int32_t, int32_t> values_;
};

}  // namespace

int main() {
  // threads are needed to RECEIVE. without a pool nobody is parked in the ioctl
  ABinderProcess_setThreadPoolMaxThreadCount(4);
  ABinderProcess_startThreadPool();

  auto service = ::ndk::SharedRefBase::make<Counter>();

  // the name has to match the descriptor, same as ILights/default on a real phone
  const std::string name = std::string(Counter::descriptor) + "/default";

  binder_status_t status =
      AServiceManager_addService(service->asBinder().get(), name.c_str());
  if (status != STATUS_OK) {
    // -8 is usually selinux saying no, or the name missing from service_contexts
    __android_log_print(ANDROID_LOG_ERROR, kTag, "addService(%s) failed: %d",
                        name.c_str(), status);
    return 1;
  }

  __android_log_print(ANDROID_LOG_INFO, kTag, "registered as %s", name.c_str());

  // parks this thread in the ioctl too, and never returns
  ABinderProcess_joinThreadPool();
  return 1;
}
