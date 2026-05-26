<p align="center">
  <img src="assets/scribd.svg" alt="Scribd" width="200">
</p>

<h1 align="center">Scribd Downloader Parallel</h1>

<p align="center">
  <b>A fork of Scribd Downloader with a web UI, batch input, parallel browser workers, retries, stop, and resume.</b>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.9+">
  </a>
  <a href="https://pypi.org/project/selenium/">
    <img src="https://img.shields.io/badge/Selenium-4.32+-green?style=for-the-badge&logo=selenium&logoColor=white" alt="Selenium 4.32+">
  </a>
  <a href="https://flask.palletsprojects.com/">
    <img src="https://img.shields.io/badge/Flask-3.0+-black?style=for-the-badge&logo=flask&logoColor=white" alt="Flask 3.0+">
  </a>
  <a href="https://github.com/niseruu/scribd-downloader-Parallel/stargazers">
    <img src="https://img.shields.io/github/stars/niseruu/scribd-downloader-Parallel?style=for-the-badge&logo=github" alt="GitHub Stars">
  </a>
</p>

---

## Fork Notice

This repository is a fork of [themrsami/scribd-downloader](https://github.com/themrsami/scribd-downloader).

The original project provides the core Selenium-based Scribd-to-PDF downloader. This fork keeps that downloader and adds a browser-based workflow for larger download runs:

- Flask web UI in `web.py`
- Batch URL extraction from pasted text
- Parallel Chrome workers
- Per-folder output under `downloads/`
- `download_log.txt` resume tracking
- Duplicate URL skipping
- Stop button for active web jobs
- Retry handling with browser restart
- CLI batch mode using the same downloader logic

---

## Features

- **Web UI** - Paste a folder name and a list of Scribd URLs, then watch live progress in the browser.
- **Parallel downloads** - Run multiple Chrome instances at the same time for faster batch jobs.
- **Batch input** - Paste one URL per line or mixed text; valid Scribd links are extracted automatically.
- **Resume support** - Completed URLs are recorded in `downloads/<folder>/download_log.txt` and skipped on later runs.
- **Duplicate detection** - Repeated URLs in the same submission are skipped before the job starts.
- **Stop button** - Cancel remaining work from the web UI while keeping already-saved PDFs.
- **Retry on failure** - Each URL is retried up to 3 times with a fresh browser if needed.
- **Custom output folders** - Keep different download sets separated under `downloads/`.
- **CLI single or batch mode** - Use the terminal workflow when you do not need the web UI.
- **Reliable PDF export** - Uses headless Chrome, dynamic page sizing, streamed PDF export, longer timeouts, and render-settle checks.
- **Scribd URL support** - Works with `/document/...` and legacy `/doc/...` links.
- **No Scribd login required** - Designed for publicly accessible Scribd document pages.

---

## Requirements

- Python 3.9 or newer
- Google Chrome installed
- Chrome WebDriver support through Selenium Manager

---

## Installation

1. Clone this fork:

   ```bash
   git clone https://github.com/niseruu/scribd-downloader-Parallel.git
   cd scribd-downloader-Parallel
   ```

2. Optional but recommended: create a virtual environment.

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

   On Windows PowerShell:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

### Web UI

Use the command set for your operating system, then open the local URL below.

#### Linux

```bash
cd scribd-downloader-Parallel
source .venv/bin/activate
python3 web.py
```

#### macOS

```bash
cd scribd-downloader-Parallel
source .venv/bin/activate
python3 web.py
```

If `python3` is not available on macOS, install Python from [python.org](https://www.python.org/downloads/) or Homebrew first.

#### Windows PowerShell

```powershell
cd scribd-downloader-Parallel
.\.venv\Scripts\Activate.ps1
py web.py
```

If PowerShell blocks the virtual environment activation script, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate the environment again.

After the server starts, open this URL in your browser:

```text
http://localhost:5000
```

Fill in:

- **Folder Name** - PDFs are saved to `downloads/<folder name>/`.
- **Links** - Paste one or more Scribd document URLs. Mixed text is okay.
- **Parallel Browsers** - Number of Chrome workers to run at once. The default is `3`.

Click **Download All**. The UI streams progress logs until the job finishes.

Use **Stop** to cancel remaining downloads. Files already saved before cancellation stay in the output folder.

To resume a batch, submit the same folder name and links again. URLs already present in `download_log.txt` are skipped.

### CLI

Run the terminal workflow with the command set for your operating system.

#### Linux

```bash
cd scribd-downloader-Parallel
source .venv/bin/activate
python3 scribd-downloader.py
```

#### macOS

```bash
cd scribd-downloader-Parallel
source .venv/bin/activate
python3 scribd-downloader.py
```

#### Windows PowerShell

```powershell
cd scribd-downloader-Parallel
.\.venv\Scripts\Activate.ps1
py scribd-downloader.py
```

Choose:

- `1` for a single Scribd URL
- `2` for batch mode

Batch mode accepts one URL per line or pasted mixed text. Press Enter on an empty line when done.

---

## Output Structure

Web UI downloads are saved like this:

```text
downloads/
  My Folder/
    document-one.pdf
    document-two.pdf
    download_log.txt
```

The log file stores completed URLs in this format:

```text
URL | filename.pdf | YYYY-MM-DD HH:MM:SS
```

---

## How It Works

1. Scribd `/document/...` or `/doc/...` URLs are converted to embed URLs.
2. Chrome opens the Scribd embed in headless mode.
3. The downloader scrolls through the document to trigger lazy-loaded pages.
4. Cookie banners, toolbars, and overlays are hidden or removed.
5. The renderer waits for fonts, images, and layout to settle.
6. The page size is detected from Scribd's rendered page wrapper.
7. Chrome DevTools Protocol exports the PDF, using stream mode for large files.
8. The web UI assigns batches across multiple worker browsers when parallel mode is used.

---

## Tuning

Large or image-heavy documents may need more time. These environment variables are supported:

| Variable | Default | Description |
| --- | --- | --- |
| `SCRIBD_CDP_TIMEOUT` | `600` | ChromeDriver command timeout in seconds for PDF export |
| `SCRIBD_RENDER_SETTLE_TIMEOUT` | `30` | Maximum time to wait for fonts, images, and layout to settle |
| `SCRIBD_SCROLL_DELAY` | `0.15` | Delay between scroll steps while loading pages |
| `SCRIBD_PDF_STREAM_CHUNK_SIZE` | `1048576` | Chunk size for streamed PDF output |
| `SCRIBD_HEADLESS` | `1` | Set to `0` to run Chrome visibly for debugging |

Example:

```bash
SCRIBD_CDP_TIMEOUT=900 SCRIBD_RENDER_SETTLE_TIMEOUT=45 python web.py
```

On Windows PowerShell:

```powershell
$env:SCRIBD_CDP_TIMEOUT="900"
$env:SCRIBD_RENDER_SETTLE_TIMEOUT="45"
python web.py
```

---

## Troubleshooting

### ChromeDriver issues

Selenium Manager should handle ChromeDriver automatically. If browser startup fails, update Selenium:

```bash
pip install --upgrade selenium
```

### Web UI starts but downloads do not run

- Make sure Chrome is installed.
- Try lowering **Parallel Browsers** to `1` or `2` if your machine is low on RAM.
- Check the terminal running `python web.py` for backend errors.

### PDFs are blank or incomplete

- Some documents may be protected or not fully accessible.
- Try `SCRIBD_HEADLESS=0` to watch Chrome load the page.
- Increase `SCRIBD_SCROLL_DELAY` and `SCRIBD_RENDER_SETTLE_TIMEOUT`.

### Resume skips a URL unexpectedly

Check:

```text
downloads/<folder>/download_log.txt
```

Remove the relevant line if you want to force that URL to download again.

---

## Prompt Helpers

This fork also includes prompt templates under `prompts/` for document extraction workflows:

- `npwp_qwen3_vl_json_extraction.md`
- `siup_qwen3_vl_json_extraction.md`
- `npwp_siup_crosscheck_json_prompt.md`

These files are separate helpers and are not required for the Scribd download runtime.

---

## Credits

- Fork maintained at [niseruu/scribd-downloader-Parallel](https://github.com/niseruu/scribd-downloader-Parallel)
- Original project by [Usama Nazir / themrsami](https://github.com/themrsami): [themrsami/scribd-downloader](https://github.com/themrsami/scribd-downloader)

---

## Disclaimer

This tool is for educational purposes only. Respect copyright laws, Scribd's Terms of Service, and only download documents you have the right to access.
