---
title: Home
layout: default
nav_order: 1
---

# Android Notebook

How Android actually works, checked on a real production phone.

**Target:** SM-S942B (Galaxy S26, Exynos 2600) · `S942BXXS4AZG5` · Android 16

{: .note }
Every claim here comes with the command that verifies it. If a chapter says something
I have not run myself, it says so.

## Rules

1. one chapter = one mechanism, traced end to end
2. every claim carries the command that proves it
3. firmware version at the top of every chapter — this rots otherwise
4. never write about something I have not run

## Chapters

| # | Chapter | Status |
|---|---|---|
| 01 | [app components & the manifest](01-app-components) | written |
| 02 | binder: `transact` → `onTransact` | |
| 03 | system service | in progress |
| 04 | HAL service & native daemon | |
| 05 | `.so`, linker, `dlopen`, name mangling | |
| 06 | permission vs SELinux — two gates | |
| 07 | sandbox: uid, zygote fork, what is inherited | |
| 08 | media pipeline: extractor → codec | |
| 09 | RIL & the modem | |
| 10 | mitigations measured on this device | |

## Hands-on — `surfacemap`

One tool, grown one module per chapter. Input: a connected device. Output: its complete
attack surface across all four service kinds.

    ch01  ->  parse every manifest, list exported components with no permission
    ch03  ->  join `service list` to $Stub$Proxy methods
    ch04  ->  lshal + every `service` block in *.rc
    ch06  ->  join all of it to service_contexts + sepolicy: who reaches what

By chapter 6 it answers, for one device: **what can a zero-permission app touch?**

## Reading

- [cs.android.com](https://cs.android.com/android/platform/superproject/main) — AOSP source, no clone needed
- [AOSP architecture](https://source.android.com/docs/core/architecture)
