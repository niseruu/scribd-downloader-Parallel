"""
Scribd Downloader — Web UI
==========================

Flask app with two inputs (folder name, list of links) and real-time
progress streaming via Server-Sent Events.

Supports concurrent downloads and a stop button to cancel in-progress jobs.

Usage:
    python web.py
    Then open http://localhost:5000 in your browser.
"""

import importlib
import io
import json
import os
import queue
import re
import shutil
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Flask, Response, jsonify, render_template_string, request

# Import the hyphenated module
_downloader = importlib.import_module("scribd-downloader")

build_chrome_options = _downloader.build_chrome_options
download_document = _downloader.download_document
extract_urls_from_text = _downloader.extract_urls_from_text

app = Flask(__name__)

# Active jobs: job_id -> {"queue": Queue, "cancel": Event}
_jobs: dict[str, dict] = {}

DOWNLOADS_ROOT = os.path.join(os.getcwd(), "downloads")
DOWNLOAD_LOG_FILENAME = "download_log.txt"
_log_lock = threading.Lock()

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Scribd Downloader</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: #0f1117;
    color: #e0e0e0;
    min-height: 100vh;
    display: flex;
    justify-content: center;
    padding: 40px 16px;
  }
  .container { max-width: 720px; width: 100%; }
  h1 {
    font-size: 1.6rem;
    font-weight: 600;
    margin-bottom: 24px;
    color: #fff;
  }
  label {
    display: block;
    font-size: 0.85rem;
    font-weight: 500;
    margin-bottom: 6px;
    color: #aaa;
  }
  input[type="text"], input[type="number"], textarea {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid #2a2d3a;
    border-radius: 8px;
    background: #1a1d2e;
    color: #e0e0e0;
    font-size: 0.95rem;
    font-family: inherit;
    outline: none;
    transition: border-color .15s;
  }
  input[type="text"]:focus, input[type="number"]:focus, textarea:focus {
    border-color: #5b6eef;
  }
  input[type="number"] { width: 100px; }
  textarea {
    min-height: 200px;
    resize: vertical;
    font-family: "SF Mono", "Fira Code", monospace;
    font-size: 0.85rem;
    line-height: 1.5;
  }
  .field { margin-bottom: 18px; }
  .hint { font-size: 0.75rem; color: #666; margin-top: 4px; }
  .btn-row { display: flex; gap: 10px; align-items: center; }
  button {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 24px;
    border: none;
    border-radius: 8px;
    color: #fff;
    font-size: 0.95rem;
    font-weight: 500;
    cursor: pointer;
    transition: background .15s;
  }
  #btn { background: #5b6eef; }
  #btn:hover { background: #4a5cd8; }
  #btn:disabled { opacity: .5; cursor: not-allowed; }
  #stop-btn { background: #dc2626; display: none; }
  #stop-btn:hover { background: #b91c1c; }
  #stop-btn:disabled { opacity: .5; cursor: not-allowed; }
  #stop-btn.visible { display: inline-flex; }
  #log-section {
    margin-top: 28px;
    display: none;
  }
  #log-section.visible { display: block; }
  #log {
    background: #111320;
    border: 1px solid #2a2d3a;
    border-radius: 8px;
    padding: 14px 16px;
    font-family: "SF Mono", "Fira Code", monospace;
    font-size: 0.8rem;
    line-height: 1.6;
    max-height: 420px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-all;
  }
  .log-info { color: #8b95a5; }
  .log-success { color: #34d399; }
  .log-error { color: #f87171; }
  .log-progress { color: #60a5fa; }
  .log-warn { color: #fbbf24; }
  #summary {
    margin-top: 16px;
    padding: 14px 16px;
    border-radius: 8px;
    display: none;
  }
  #summary.done { display: block; background: #162316; border: 1px solid #22543d; }
  #summary.has-errors { background: #261616; border: 1px solid #742a2a; }
  .spinner {
    width: 18px; height: 18px;
    border: 2px solid transparent;
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin .6s linear infinite;
    display: none;
  }
  button.loading .spinner { display: inline-block; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="container">
  <h1>Scribd Downloader</h1>

  <form id="form">
    <div class="field">
      <label for="folder">Folder Name</label>
      <input type="text" id="folder" name="folder" placeholder="e.g. NPWP Documents" required>
      <div class="hint">PDFs will be saved to <code>downloads/&lt;folder name&gt;/</code></div>
    </div>
    <div class="field">
      <label for="links">Links</label>
      <textarea id="links" name="links" placeholder="Paste Scribd links here, one per line..." required></textarea>
      <div class="hint">Supports mixed text — Scribd URLs will be auto-extracted</div>
    </div>
    <div class="field">
      <label for="concurrency">Parallel Browsers</label>
      <input type="number" id="concurrency" name="concurrency" value="3" min="1" max="20">
      <div class="hint">Number of browsers to run in parallel (URLs are split evenly across them)</div>
    </div>
    <div class="btn-row">
      <button type="submit" id="btn">
        <span class="spinner"></span>
        <span class="btn-text">Download All</span>
      </button>
      <button type="button" id="stop-btn">Stop</button>
    </div>
  </form>

  <div id="log-section">
    <label>Progress</label>
    <div id="log"></div>
  </div>
  <div id="summary"></div>
</div>

<script>
const form = document.getElementById('form');
const btn = document.getElementById('btn');
const btnText = btn.querySelector('.btn-text');
const stopBtn = document.getElementById('stop-btn');
const logSection = document.getElementById('log-section');
const logEl = document.getElementById('log');
const summaryEl = document.getElementById('summary');
let evtSource = null;
let currentJobId = null;

function appendLog(text, cls) {
  const span = document.createElement('span');
  span.className = cls || 'log-info';
  span.textContent = text + '\n';
  logEl.appendChild(span);
  logEl.scrollTop = logEl.scrollHeight;
}

function resetUI() {
  btn.classList.remove('loading');
  btn.disabled = false;
  btnText.textContent = 'Download All';
  stopBtn.classList.remove('visible');
  stopBtn.disabled = false;
  currentJobId = null;
}

stopBtn.addEventListener('click', async () => {
  if (!currentJobId) return;
  stopBtn.disabled = true;
  try {
    await fetch('/api/stop/' + currentJobId, { method: 'POST' });
    appendLog('Stop requested — waiting for active downloads to finish...', 'log-warn');
  } catch (err) {
    appendLog('Failed to send stop: ' + err, 'log-error');
  }
});

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (evtSource) { evtSource.close(); evtSource = null; }

  const folder = document.getElementById('folder').value.trim();
  const links = document.getElementById('links').value.trim();
  const concurrency = parseInt(document.getElementById('concurrency').value) || 1;
  if (!folder || !links) return;

  // Reset UI
  logEl.innerHTML = '';
  summaryEl.style.display = 'none';
  summaryEl.className = '';
  logSection.classList.add('visible');
  btn.classList.add('loading');
  btn.disabled = true;
  btnText.textContent = 'Downloading...';
  stopBtn.classList.add('visible');
  stopBtn.disabled = false;

  try {
    const resp = await fetch('/api/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder, links, concurrency })
    });
    const data = await resp.json();

    if (data.error) {
      appendLog('Error: ' + data.error, 'log-error');
      resetUI();
      return;
    }

    currentJobId = data.job_id;
    let msg = `Found ${data.count} document(s). Downloading with ${data.concurrency} worker(s)...`;
    if (data.skipped > 0) {
      msg += ` (${data.skipped} duplicate(s) skipped)`;
    }
    appendLog(msg, 'log-progress');

    // SSE stream
    evtSource = new EventSource('/api/stream/' + data.job_id);
    evtSource.addEventListener('log', (e) => {
      appendLog(e.data, 'log-info');
    });
    evtSource.addEventListener('progress', (e) => {
      appendLog(e.data, 'log-progress');
    });
    evtSource.addEventListener('success', (e) => {
      appendLog(e.data, 'log-success');
    });
    evtSource.addEventListener('error_msg', (e) => {
      appendLog(e.data, 'log-error');
    });
    evtSource.addEventListener('warn', (e) => {
      appendLog(e.data, 'log-warn');
    });
    evtSource.addEventListener('done', (e) => {
      const result = JSON.parse(e.data);
      evtSource.close();
      evtSource = null;
      resetUI();

      let html = `<strong>Done!</strong> ${result.succeeded}/${result.total} succeeded`;
      if (result.failed > 0) html += `, <span style="color:#f87171">${result.failed} failed</span>`;
      if (result.cancelled > 0) html += `, <span style="color:#fbbf24">${result.cancelled} cancelled</span>`;
      html += `<br><small>Saved to: ${result.folder}</small>`;
      summaryEl.innerHTML = html;
      summaryEl.className = (result.failed > 0 || result.cancelled > 0) ? 'done has-errors' : 'done';
      summaryEl.style.display = 'block';
    });
    evtSource.onerror = () => {
      evtSource.close();
      evtSource = null;
      resetUI();
    };
  } catch (err) {
    appendLog('Request failed: ' + err, 'log-error');
    resetUI();
  }
});
</script>
</body>
</html>
"""


class LogCapture(io.TextIOBase):
    """A write-only stream that forwards print() output to an SSE queue."""

    def __init__(self, q: queue.Queue, original_stdout):
        self._q = q
        self._orig = original_stdout

    def write(self, text):
        if not text or text.strip() == "":
            return len(text)
        self._orig.write(text)
        self._orig.flush()
        self._q.put(("log", text.rstrip("\n")))
        return len(text)

    def flush(self):
        self._orig.flush()


def _sanitize_folder_name(name: str) -> str:
    """Remove path separators and dangerous characters from folder name."""
    name = name.strip()
    name = re.sub(r'[/\\:*?"<>|]', "_", name)
    name = name.strip(". ")
    return name or "scribd_downloads"


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/download", methods=["POST"])
def start_download():
    data = request.get_json(force=True)
    folder_raw = data.get("folder", "").strip()
    links_text = data.get("links", "").strip()
    concurrency = data.get("concurrency", 1)

    if not folder_raw:
        return jsonify(error="Folder name is required."), 400
    if not links_text:
        return jsonify(error="No links provided."), 400

    try:
        concurrency = max(1, min(20, int(concurrency)))
    except (TypeError, ValueError):
        concurrency = 1

    folder_name = _sanitize_folder_name(folder_raw)
    urls = extract_urls_from_text(links_text)

    # Deduplicate and track skipped
    seen = set()
    unique = []
    duplicates = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
        else:
            duplicates.append(u)
    urls = unique

    if not urls:
        return jsonify(error="No valid Scribd URLs found in the input."), 400

    job_id = uuid.uuid4().hex
    q: queue.Queue = queue.Queue()
    cancel_event = threading.Event()
    _jobs[job_id] = {"queue": q, "cancel": cancel_event}

    output_dir = os.path.join(DOWNLOADS_ROOT, folder_name)

    thread = threading.Thread(
        target=_run_job,
        args=(job_id, q, cancel_event, urls, duplicates, output_dir, concurrency),
        daemon=True,
    )
    thread.start()

    return jsonify(job_id=job_id, count=len(urls), skipped=len(duplicates), concurrency=concurrency)


@app.route("/api/stop/<job_id>", methods=["POST"])
def stop_job(job_id):
    job = _jobs.get(job_id)
    if job is None:
        return jsonify(error="Job not found"), 404
    job["cancel"].set()
    return jsonify(ok=True)


def _read_completed_urls(output_dir):
    """Read URLs already downloaded from the log file."""
    log_path = os.path.join(output_dir, DOWNLOAD_LOG_FILENAME)
    completed = set()
    if os.path.isfile(log_path):
        with open(log_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Format: URL | filename | timestamp
                    parts = line.split(" | ")
                    if parts:
                        completed.add(parts[0].strip())
    return completed


def _append_to_log(output_dir, url, filename):
    """Append a completed download entry to the log file (thread-safe)."""
    log_path = os.path.join(output_dir, DOWNLOAD_LOG_FILENAME)
    os.makedirs(output_dir, exist_ok=True)
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _log_lock:
        with open(log_path, "a") as f:
            f.write(f"{url} | {filename} | {timestamp}\n")


MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 3


def _worker_loop(worker_id, url_batch, total_urls, offset, output_dir, q, cancel_event):
    """
    Each worker owns ONE Chrome browser and processes its assigned URLs
    sequentially within that browser, retrying on failure.
    """
    import time as _time
    from selenium import webdriver

    worker_name = f"W_{worker_id}"
    results = []  # list of (url, status, path)

    driver = None
    runtime_profile_dir = None

    def _start_browser():
        nonlocal driver, runtime_profile_dir
        profile_id = f"{worker_name}-{uuid.uuid4().hex[:6]}"
        opts, prof_dir = build_chrome_options(profile_suffix=profile_id)
        runtime_profile_dir = prof_dir
        driver = webdriver.Chrome(options=opts)
        return driver

    def _close_browser():
        nonlocal driver, runtime_profile_dir
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
            driver = None
        if runtime_profile_dir and os.path.isdir(runtime_profile_dir):
            shutil.rmtree(runtime_profile_dir, ignore_errors=True)
            runtime_profile_dir = None

    try:
        _start_browser()
        q.put(("log", f"({worker_name}) Browser started — assigned {len(url_batch)} URL(s)"))

        for local_i, url in enumerate(url_batch):
            global_i = offset + local_i + 1
            if cancel_event.is_set():
                results.append((url, "cancelled", None))
                continue

            q.put(("progress", f"[{global_i}/{total_urls}] ({worker_name}) {url}"))
            last_error = None

            for attempt in range(1, MAX_RETRIES + 1):
                if cancel_event.is_set():
                    break

                try:
                    saved = download_document(driver, url, output_dir=output_dir)
                    if cancel_event.is_set():
                        break
                    if saved:
                        _append_to_log(output_dir, url, os.path.basename(saved))
                        q.put(("success", f"✓ ({worker_name}) Saved: {os.path.basename(saved)}"))
                        results.append((url, "ok", saved))
                        last_error = None
                        break
                    else:
                        last_error = "Download returned no file"
                except Exception as exc:
                    last_error = str(exc)

                # On failure, restart the browser and retry
                if attempt < MAX_RETRIES and not cancel_event.is_set():
                    q.put(("warn", f"⟳ ({worker_name}) Attempt {attempt}/{MAX_RETRIES} failed: {last_error}. Restarting browser..."))
                    _close_browser()
                    _time.sleep(RETRY_DELAY_SECONDS)
                    try:
                        _start_browser()
                    except Exception as restart_err:
                        q.put(("error_msg", f"✗ ({worker_name}) Browser restart failed: {restart_err}"))
                        last_error = str(restart_err)
                        break

            if cancel_event.is_set() and not any(r[0] == url for r in results):
                results.append((url, "cancelled", None))
            elif last_error:
                q.put(("error_msg", f"✗ ({worker_name}) Failed after {MAX_RETRIES} attempts: {url} — {last_error}"))
                results.append((url, "failed", None))

    except Exception as exc:
        q.put(("error_msg", f"✗ ({worker_name}) Fatal worker error: {exc}"))
        # Mark remaining URLs as failed
        processed = {r[0] for r in results}
        for url in url_batch:
            if url not in processed:
                results.append((url, "failed", None))
    finally:
        _close_browser()

    return results


def _run_job(
    job_id: str,
    q: queue.Queue,
    cancel_event: threading.Event,
    urls: list[str],
    duplicates: list[str],
    output_dir: str,
    concurrency: int,
):
    """Orchestrator: split URLs across N workers, each with its own browser."""
    succeeded = 0
    failed = 0
    cancelled = 0

    old_stdout = sys.stdout
    sys.stdout = LogCapture(q, old_stdout)

    try:
        if duplicates:
            q.put(("progress", f"Skipped {len(duplicates)} duplicate link(s):"))
            for dup in duplicates:
                q.put(("log", f"  ⊘ {dup}"))

        q.put(("progress", f"Saving to: {output_dir}"))

        # Check which URLs were already downloaded in a previous run
        already_done = _read_completed_urls(output_dir)
        pending_urls = []
        for url in urls:
            if url in already_done:
                q.put(("warn", f"⊘ Already downloaded, skipping: {url}"))
                succeeded += 1
            else:
                pending_urls.append(url)

        if not pending_urls:
            q.put(("progress", "All documents already downloaded."))
        else:
            actual_concurrency = min(concurrency, len(pending_urls))
            q.put(("progress", f"Launching {actual_concurrency} browser(s) for {len(pending_urls)} document(s)..."))

            # Split URLs round-robin across workers
            batches: list[list[str]] = [[] for _ in range(actual_concurrency)]
            for i, url in enumerate(pending_urls):
                batches[i % actual_concurrency].append(url)

            # Compute global offset per worker for display numbering
            offsets = []
            acc = 0
            # The round-robin means URLs aren't contiguous, so just use a counter
            # We'll pass total and let the worker compute global index
            with ThreadPoolExecutor(max_workers=actual_concurrency, thread_name_prefix="W") as pool:
                futures = []
                offset = 0
                for wid, batch in enumerate(batches):
                    fut = pool.submit(
                        _worker_loop, wid, batch, len(pending_urls), offset,
                        output_dir, q, cancel_event
                    )
                    futures.append(fut)
                    offset += len(batch)

                for fut in as_completed(futures):
                    for _url, status, _path in fut.result():
                        if status == "ok":
                            succeeded += 1
                        elif status == "cancelled":
                            cancelled += 1
                        else:
                            failed += 1

        if cancel_event.is_set():
            q.put(("warn", "Job was stopped by user."))

    except Exception as exc:
        q.put(("error_msg", f"Fatal error: {exc}"))
    finally:
        sys.stdout = old_stdout

        q.put((
            "done",
            json.dumps({
                "succeeded": succeeded,
                "failed": failed,
                "cancelled": cancelled,
                "total": len(urls),
                "folder": output_dir,
            }),
        ))

        def _cleanup():
            import time
            time.sleep(30)
            _jobs.pop(job_id, None)
        threading.Thread(target=_cleanup, daemon=True).start()


@app.route("/api/stream/<job_id>")
def stream(job_id):
    job = _jobs.get(job_id)
    if job is None:
        return "Job not found", 404

    q = job["queue"]

    def generate():
        while True:
            try:
                event_type, data = q.get(timeout=600)
            except queue.Empty:
                break
            yield f"event: {event_type}\ndata: {data}\n\n"
            if event_type == "done":
                break

    return Response(generate(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


if __name__ == "__main__":
    print(f"Downloads will be saved to: {DOWNLOADS_ROOT}")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
