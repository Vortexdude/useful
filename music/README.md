Usage -- one script, three commands
# 1. Sync a YouTube Music playlist with local files
```python
python music_manager.py sync "https://music.youtube.com/playlist?list=PLxxxxxx"
python music_manager.py sync --dry-run --no-rename "URL"

# 2. Build the CSV catalog of all local music
python music_manager.py catalog
python music_manager.py catalog --append --show-untagged
 
# 3. Organize files into categorized folders
python music_manager.py organize --dry-run
python music_manager.py organize

```
