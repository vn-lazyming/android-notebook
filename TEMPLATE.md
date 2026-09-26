# Chapter template

Copy this into `src/NN-name.md`. Every chapter answers the same six questions in the same
order. Section 2 is the heart — that is where this notebook differs from every other one.

---

    Verified on SM-S942B · S942BXXS4AZG5 · Android 16 · 2026-MM-DD
    AOSP source read at <branch/tag>

## 1. Why this exists

The problem the mechanism solves. Two paragraphs, no code. If you cannot say what breaks
without it, you do not understand it yet.

## 2. Build one

The heart of the chapter. Not "here is the API" — **here is the smallest thing that works,
written from nothing**, every file, in the order a developer writes them.

    2.1  the smallest working version    complete, compiles, runs
    2.2  what each file is for           one line each, no file unexplained
    2.3  what the build generates        show the generated code, not a description of it
    2.4  run it, show the output

The rule: a reader who copies section 2 gets a running thing. No "...", no "left as an
exercise". If a step needs a platform build you cannot do, say so and give the closest
runnable analogue.

## 3. What AOSP really does

Now read a real one, with the toy fresh in mind. Quote real source with a real link:

    frameworks/base/services/core/java/com/android/server/AlarmManagerService.java:412
    https://cs.android.com/...

Where does the real one differ from the toy, and why. The differences are almost always
the interesting part: threading, lifecycle, caching, permission.

## 4. Where the gate is

Falls out of sections 2 and 3 by itself. Which line is the check. Who wrote it — the
system, or a human. Human-written gates are where bugs live.

## 5. The surface

What an attacker sees. Who can reach it, from which uid and SELinux domain, through which
node. What is left if the gate is missing.

## 6. Verify

Commands with their real output from this device. Not what the output should be — what it
was, pasted.

## 7. Traps

Every way you can measure this wrong and get a false clean. Name the wrong method, then
the right one. This section is the whole value of the notebook.
