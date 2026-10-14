# Mobile Release Process

Owner: Mobile Platform

## Applications

Larkspur ships two mobile applications: the customer app (iOS and Android)
and the field-operations app (Android only). Both are built from the
`mobile` monorepo with React Native and Expo, with native modules in Swift
and Kotlin where required.

## Weekly train

The mobile train is cut every Tuesday at 10:00 UTC from `main`. The build is
distributed to internal testers through TestFlight and the Play internal
track within an hour. After a 24-hour soak, the release manager submits to
both stores on Wednesday. Store review typically completes within 24 hours
for iOS and a few hours for Android.

## Staged rollout

Releases roll out in stages: 5% of users on day one, 25% on day two, 50% on
day three and 100% on day four, if crash-free sessions stay above 99.5% and
no new crash signature affects more than 0.1% of sessions. The release
manager can halt a rollout from the store console at any stage.

## Hotfixes

A mobile hotfix is reserved for crashes above the threshold, data loss or
security issues. It is branched from the released tag, cherry-picked to
`main`, and submitted with an expedited review request. Hotfixes land within
24 hours in most cases but the timing is not guaranteed.

## Over-the-air updates

JavaScript-only changes can ship as over-the-air (OTA) updates through Expo
Updates without a store release. OTA is used for bug fixes and copy changes,
never for features that change native code or permissions. OTA updates are
rolled back by publishing the previous bundle.

## Minimum OS versions

The customer app supports iOS versions released in the last three years and
Android API level 28 and above. Dropping a version requires 90 days of
notice in release notes and an in-app message to affected users.

## Crash monitoring

Crashes are reported to Sentry with the release and build number. A new crash
signature affecting more than 0.1% of sessions pages the Mobile Platform
on-call. Crash-free sessions per release are shown on the mobile dashboard.

## Store metadata

Screenshots, descriptions and release notes are stored in the `mobile`
repository under `store/` and uploaded by CI with `fastlane`. Editing store
metadata in the store console directly is not allowed; the next CI upload
overwrites it.
