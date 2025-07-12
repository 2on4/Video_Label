# Video Labels Organizer

A Python application to scan directories for video files, identify content using Google's Gemini AI, and organize them into media server-compatible structures (e.g., for Plex, Jellyfin, Emby, Kodi).

## Features
- Recursive scanning for video files (mp4, mkv, avi, etc.)
- **Efficient AI processing** - Single batch request to Gemini 2.5 Pro for all files (cost-effective)
- AI-powered identification of TV shows and movies from filenames using Gemini 2.5 Pro
- Automatic renaming and directory organization following exact conventions
- Dry-run mode for previews
- Logging, error handling, and undo via operation logs
- Beginner-friendly Tkinter GUI
- Cross-platform (Windows, macOS, Linux)
- Duplicate detection with quality prioritization (resolution or file size)

## Setup Instructions (For Complete Beginners)
1. **Install Python**: Download and install Python 3.10+ from python.org. Check "Add to PATH" during installation.
2. **Create Project Folder**: Make a folder named "Video Labels" on your desktop.
3. **Copy Files**: Create subfolders `src/`, `tests/`, `config/`. Copy the code files into them as described.
4. **Install Dependencies**: Open a terminal/command prompt in the project folder and run:
   ```
   python -m pip install -r requirements.txt
   ```
5. **Install FFmpeg** (for quality assessment): Download from ffmpeg.org/download.html. Extract and add the `bin/` folder to your system PATH (search "how to add to PATH" for your OS).
6. **Run Install Script**: In the terminal, run `python install.py`. It will install deps again if needed and prompt for your Gemini API key.
7. **Get Gemini API Key**: Go to https://aistudio.google.com/app/apikey, create a key, and paste it when prompted.

## Configuration Guide
- Edit `config/config.ini`:
  ```
  [gemini]
  api_key = your_api_key_here

  [paths]
  default_source = /path/to/videos
  default_target = /path/to/organized

  [settings]
  dry_run = True  ; Set to False for actual changes
  max_workers = 10  ; For concurrent API calls
  ```
- The app will use these defaults in the GUI, but you can override them.

## Usage Examples
1. **Launch the app**: `python run.py` (use this instead of `python src/main.py`)
2. In the GUI:
   - Select source directory (e.g., a folder with unsorted videos).
   - Select target directory (e.g., a new "Organized" folder).
   - Check "Dry Run" for preview.
   - Click "Start Organizing".
3. Example Input: Source has `The.Office.US.S01E01.mkv`
   - AI identifies as TV show "The Office (US)", S01E01.
   - Organizes to `target/TV Shows/The Office (US)/Season 01/The Office (US) - S01E01.mkv`
4. For movies: `Inception.2010.mkv` -> `target/Movies/Inception (2010)/Inception (2010).mkv`
5. Dry-run logs changes without applying them.
6. Undo: If not dry-run, operations are logged in `operations.json`. Run `python run.py --undo` (future extension; manually revert for now).

## Efficiency Improvements
- **Single AI Request**: All files are analyzed in one batch request instead of individual calls
- **Cost Effective**: Dramatically reduces API costs and token usage
- **Faster Processing**: No waiting for multiple API calls
- **Better Context**: AI can see all files together for better consistency

## Troubleshooting Guide
- **API Key Invalid**: Check `config.ini` or re-run `install.py`. Ensure key has access to Gemini 2.5 Pro.
- **ffprobe not found**: Install FFmpeg and add to PATH. Restart the app.
- **No videos found**: Ensure source has files with supported extensions (mp4, mkv, etc.).
- **API Rate Limit**: The app now uses a single request, so rate limits are less likely.
- **Permission Errors**: Run as admin or check file permissions.
- **Unknown Media**: AI couldn't identify; manually rename or improve filename.
- **GUI Issues**: Ensure Tkinter is installed (built-in with Python; on Linux, install `python3-tk`).
- **Import Errors**: Use `python run.py` instead of `python src/main.py`.

## Testing Instructions
1. Install pytest: Already in requirements.txt.
2. Run tests: `python -m pytest tests/`
3. Tests cover scanning, cleaning, AI mocking, organization logic, etc. Expect 80%+ coverage.

For issues, check `app.log` for details. 