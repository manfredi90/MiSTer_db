# MiSTer_db

A personal database for the MiSTer Downloader. Each hour `db.json` is rebuilt from the latest
full release of the cores listed in `cores.json`. Pre-releases are not included.

To use it, add this to `/media/fat/downloader.ini`:

```ini
[manfredi90_ss]
db_url = https://raw.githubusercontent.com/manfredi90/MiSTer_db/main/db.json
```
