# Changelog

## 1.0.0 — 2026-10-18

First public release.

- Local web app: scans any folder with parallel `scandir`, measuring real on-disk size (allocated blocks, hard links counted once).
- **Clean up** tab: finds `.next`, `node_modules`, Flutter `build` / `.dart_tool`, Rust `target`, CocoaPods, Xcode DerivedData / iOS DeviceSupport / Archives, Gradle / npm / Go / pip / pub caches, app caches, Docker, simulators and the Trash. Each is marked safe or check-first.
- **Explore** tab: squarified treemap plus sorted list, drill into any folder.
- **Largest files** tab: the 300 biggest files.
- Move to Trash or delete permanently; core folders, keychains, iCloud Drive, Mail, Photos, Docker data and `.git` are refused.
- Binds to 127.0.0.1 only, per-run token on every API call, Host header check.
- No dependencies beyond Python 3's standard library. Mona Sans font bundled (OFL).
