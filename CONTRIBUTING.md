# Contributing

Thanks for helping! The whole app is two files: `diskclean.py` (scanner + local server) and `index.html` (UI). No build step.

```bash
python3 diskclean.py --no-scan          # run locally
python3 -m unittest -v test_diskclean   # tests use a throwaway fake $HOME
```

Good first contributions:

- **New cleanup rules.** Add a folder pattern to `classify()` / `KIND_INFO` or a fixed location to `KNOWN_LOCATIONS` in `diskclean.py`, with a one-line explanation of what regenerates it. Only mark something `safe` if a tool recreates it automatically.
- **Safety.** Anything that could make `is_deletable()` too permissive is a bug — please add a test with the fix.

Keep it dependency-free (standard library only) and keep the UI a single HTML file.
