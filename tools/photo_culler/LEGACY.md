# Legacy 4D culler (quarantined)

This package powers `python tools/cull-photos.py ... --legacy` only.

Default gallery publish uses **PixCull offline CLI** via `tools/cull-photos.py`
(no `--legacy`). Do not add new features here; remove this package once PixCull
smoke tests are trusted on real shoots.

Legacy deps (install manually if needed):

```text
opencv-python-headless>=4.8,<5
numpy>=1.24
ultralytics>=8.0
```
