// an init service that speaks AIDL, shaped like android.hardware.light.ILights
//   .aidl  -> com/example/ICounter.aidl
//   build  -> ./build.sh
//   init   -> counterd.rc

#include <aidl/com/example/BnCounter.h>  // generated from our .aidl
#include <android/binder_manager.h>      // AServiceManager_addService
#include <android/binder_process.h>      // the thread pool
#include <android/log.h>                 // __android_log_print

#include <mutex>

#define TAG   "counterd"
#define SLOTS 8

// BnCounter is generated. we only fill in the two methods we declared
class Counter : public aidl::com::example::BnCounter {
 public:
  // set value implementation in server side
  ::ndk::ScopedAStatus setValue(int32_t id, int32_t value) override {
    if (id < 0 || id >= SLOTS) {
      return ::ndk::ScopedAStatus::fromServiceSpecificError(1);
    }

    // lock for race safe
    std::lock_guard<std::mutex> guard(lock_);
    values_[id] = value;

    // logging
    __android_log_print(ANDROID_LOG_INFO, TAG, "setValue(%d, %d) from uid %u",
                        id, value, AIBinder_getCallingUid());
    return ::ndk::ScopedAStatus::ok();
  }

  // getvalue implementation in server side
  ::ndk::ScopedAStatus getValues(std::vector<int32_t>* out) override {
    std::lock_guard<std::mutex> guard(lock_);
    out->assign(values_, values_ + SLOTS);
    return ::ndk::ScopedAStatus::ok();
  }

 private:
  std::mutex lock_;
  int32_t values_[SLOTS] = {};
};

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
