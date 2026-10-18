#!/bin/bash
# Builds a fake home folder out of APFS clones: looks like ~133 GB, costs ~7 GB of real disk.
set -e
H="${1:-$HOME/.mdc-demo}"; rm -rf "$H"; mkdir -p "$H"; cd "$H"
head -c 200000000 /dev/urandom > .seed && mkfile 6g .seed6
mk() { mkdir -p "$(dirname "$1")"; for i in $(seq 1 "$2"); do cp -c .seed "$1-$i.pack"; done; }
big() { mkdir -p "$(dirname "$1")"; cp -c .seed6 "$1"; }
mk Developer/storefront/.next/cache/webpack/client-development/chunk 210
mk Developer/storefront/node_modules/.pnpm/next/dist/chunk 7; touch Developer/storefront/package.json
mk Developer/mobile-app/build/app/outputs/apk/app 22; touch Developer/mobile-app/pubspec.yaml
mk Developer/mobile-app/.dart_tool/flutter_build/kernel 7
mk Developer/mobile-app/ios/Pods/Firebase/lib 9; touch Developer/mobile-app/ios/Podfile
mk Developer/api-server/node_modules/@prisma/engines/query 8
mk Developer/api-server/.venv/lib/python3.12/site-packages/torch/lib 25
mk Developer/rust-cli/target/debug/deps/libcli 31; touch Developer/rust-cli/Cargo.toml
mk Library/Developer/Xcode/DerivedData/MyApp-abcd/Build/obj 60
mk "Library/Developer/Xcode/iOS DeviceSupport/iPhone16,2 18.1/Symbols/lib" 100
mk Library/Developer/Xcode/Archives/2025-11-02/MyApp/dSYMs/dsym 20
mk Library/Caches/com.spotify.client/Data/blob 10
mk Library/Caches/Google/Chrome/Default/Cache/blob 8
mk Library/Containers/com.docker.docker/Data/vms/0/data/layer 80
mk .npm/_cacache/content-v2/sha512/blob 15
mk .gradle/caches/modules-2/files/blob 25
big "Movies/conference-talk-4k.mov"; big "Downloads/Install macOS Sequoia.dmg"
mkdir -p Movies/Drone; for i in 01 02 03 04 05 06 07 08 09 10 11 12; do cp -c .seed "Movies/Drone/DJI_00$i.MP4"; done
mkdir -p .Trash; rm -f .seed .seed6
