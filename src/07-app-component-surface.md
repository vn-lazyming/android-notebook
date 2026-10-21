## Android App
> this chapter is just a brief one. later i will make a detailed chapter that looks into the internal code of all these concepts

sure, first thing everybody thinks about when attacking Android is attacking the app first

### App component
https://developer.android.com/guide/components/fundamentals

in that site google says that :
> App components are the essential building blocks of an Android app. Each component is an entry point through which the system or a user can enter your app. Some components depend on others.

so every component of an app is an attack surface for us

we have 4 main app components, explained in simple terms
#### Activities
represent the code that works to `create the UI logic displayed to the User`, normally coded in Java. The bug here is a bug of Java, not memory corruption
#### Service
represent the code that works to provide some functionality `running in the background and doesn't have any UI logic`, normally coded in Java

two kinds: **started** (fire and forget, `startService`) and **bound** (the caller gets a binder back, `bindService`). the one we attack is bound, that is the one with an interface
#### Content provider
represent the code that works to give data access to other apps, exposing data through a universal resource identifier (URI) scheme beginning with content://. Other apps interact with this data if they got permission, normally coded in Java
#### Broadcast Receiver
represent the code that works to create the logic handling broadcast msgs from the phone to our app, e.g. low battery etc, or from another app, normally coded in Java

#### Manifest file
An app doesn't have a main() function to point at what code should run first, they declare in manifest file what action from the user or what msg (intent) from another app want to run which `App component`

example with Activities Component: when clicking an app, what should run ? declared like this

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application android:label="MyApp">

        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action   android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

    </application>
</manifest>
```

so there is no main(), the app only says "if you send me this intent, run this class"

- `<activity android:name=".MainActivity">` is the class that will run
- `<action android:name="android.intent.action.MAIN">` means this is the entry point of the app
- `<category android:name="android.intent.category.LAUNCHER">` means put an icon in the app drawer

when the user taps the icon, the launcher builds an intent with MAIN + LAUNCHER and sends it to
the system, the system looks in the manifest to see which class matches, and starts `MainActivity`

and this is the interesting part for us: the launcher is just another app sending an intent,
so our app can send one too. no permission, no prompt, the user taps nothing — but only if that
component is exported, see the important part below

```java
Intent i = new Intent();
i.setClassName("com.victim.app", "com.victim.app.SomeExportedActivity");
i.putExtra("data", weControlThis);
startActivity(i);
```

the other 3 components work the same way, and they have no UI so the victim sees nothing

```java
bindService(i, conn, BIND_AUTO_CREATE)              // Service
getContentResolver().call(uri, method, arg, extras) // Content provider
sendBroadcast(i)                                    // Broadcast receiver
```

adb sends the same intent, useful to try one by hand

```
adb shell am start -n com.victim.app/.SomeExportedActivity --es data value
```

#### important part

not every App component is reachable and open to the world, only App component with
`android:exported="true"` is open to the world and can be reached

and exported alone is not enough, the component can also carry `android:permission` — then the
caller must hold that permission. so it is really two conditions

- `android:exported="true"`
- and no `android:permission`

careful, `<intent-filter>` is not used to prevent other apps sending intents to you, it is just a
filter to see whether that intent is the type your app needs

google says it themselves, https://developer.android.com/guide/components/intents-filters :
> An explicit intent is always delivered to its target, regardless of any intent filters the
> component declares.
> Using an intent filter isn't a secure way to prevent other apps from starting your components.

> so after all when explore surface we just need to care about exported="true" and andoroid:permission to know can we reach that App component

#### Skill

my experience when explore this surface

##### 1. the basic commands to explore

everything starts from adb. these are the ones actually used every session

**to list the installed packages on the phone**

```
adb shell pm list packages          # everything
adb shell pm list packages -s       # system apps only   (497 on this S26)
adb shell pm list packages -3       # third party only
adb shell pm list packages -u       # include uninstalled ones
```

the `-s` list is our target list, those are the apps running with privilege, or platform app from

**how to check uid and privilege of that app**

```
adb shell dumpsys package <pkg> | grep -E "userId=|sharedUser"
```
if an app dont have higher permision or have more surface than untrusted_app attacking it is useless, you should check this first before do further action


**checking app privi with ps command**

```
adb shell ps -AZ | grep samsung
```

**how to get apk directory and how to get it**

```
adb shell pm path com.samsung.android.photoremasterservice
package:/system/priv-app/PhotoRemasterService/PhotoRemasterService.apk

adb pull /system/priv-app/PhotoRemasterService/PhotoRemasterService.apk
```

`adb shell pm path` will return more than one path if the app is split, that is one version not many, take all of them because the native .so are in the split_config one

**right way to dump full manifest file of that app**

```
apkanalyzer manifest print app.apk
```

or open the apk in jadx and read the manifest there

`aapt2 dump xmltree --file AndroidManifest.xml app.apk` works too, but it prints the **full
namespace uri** instead of `android:`, so a regex for `android:exported` matches nothing and every
app comes back clean

```
A: http://schemas.android.com/apk/res/android:exported(0x01010010)=true
```

**dont recommend you to do like this**

```
adb shell dumpsys package com.victim.app
```

shows the declared components, the permissions it holds, the uid, install path

but this is a **summary, not the full manifest**, that tables only list components that declare an `<intent-filter>`, so an exported component with no filter, the shape we want, not there very dangerous

**check define of an permission**

```
adb shell pm list permissions -f | grep -A4 com.samsung.android.permission.LOCK_TASK_MODE
  package:android
  protectionLevel:normal
```

`normal` means any app just asks for it and gets it, so that component is not protected at all.
the short form works too

```
adb shell dumpsys package permission com.samsung.android.permission.LOCK_TASK_MODE
    uid=1000 gids=[] type=0 prot=normal
```

**you can also send intent by using adb**, 

```
adb shell am start -n com.victim.app/.SomeActivity --es key value   # activity
adb shell am start-service -n com.victim.app/.SomeService           # service
adb shell am broadcast -a com.victim.app.ACTION                     # receiver
adb shell content call --uri content://com.victim.app.provider --method foo   # provider
```

careful, `adb shell` is not a normal app, it is uid 2000 in the `shell` selinux domain and it may have reachabilty from an untrusted_app maybe untrusted_app can reach or can reach you should try to create untrustep app to test 

**watch what happens**

```
adb logcat -c                       # clear first
adb logcat | grep -i victim         # then trigger, and read
```

a SecurityException in logcat is the answer to "is this gated", and it names the permission

