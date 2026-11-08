# Architecture

## Product flow

```text
Image → ordered track list → user review → YouTube candidates → user selection
      → queue confirmation → sequential playback
```

The image flow does not start a YouTube search before the user confirms the
recognized track list. It does not choose a search result automatically. Each
candidate remains attached to the source track's original position.

## Module responsibilities

- `main.py`: CLI input, track review, candidate selection, queue confirmation,
  playback approval, and user-facing queue status.
- `agent/brain.py`: Ollama requests, image recognition, and strict validation of
  ordered `MusicTrack` records.
- `agent/tools.py`: constructs browser operations and dispatches candidate
  searches and queue playback.
- `music/models.py`: browser-independent track, candidate, and status models.
- `music/queue.py`: maintains original order and each track's playback state;
  it has no Playwright dependency.
- `browser/controller.py`: YouTube candidate extraction in an isolated
  Playwright browser, and ordered playback coordination.
- `browser/youtube_player.py`: local, short-lived page hosting the official
  YouTube IFrame Player API, plus playback-state event collection.
- `config/settings.py`: Ollama endpoint, model, browser visibility, and the
  Playwright browser channel used for candidate searches.

## Track and queue states

Every track has a 1-based `position`, title, optional artist, and ambiguity
information. An unreadable item remains in that position and must be corrected
before searching.

The queue uses these states:

- `PENDING`: no candidate was confirmed, or the user marked the track unmatched.
- `SELECTED`: the user chose a YouTube candidate; ready for playback.
- `PLAYED`: the YouTube IFrame API reported the selected video's end.
- `FAILED`: candidate search, browser loading, or playback failed.

No track is removed after a search or playback error. Failures are recorded on
the corresponding queue entry, and playback continues with the next selected
track.

## Playback lifecycle

1. The CLI displays the complete queue and asks for final playback approval.
2. `BrowserController.play_queue` starts a loopback HTTP server serving a local
   player page and opens it in the system browser. Pending tracks are omitted,
   while selected video IDs are passed in original queue order.
3. The page uses YouTube's official IFrame Player API. A user click starts the
   playlist once, satisfying browser autoplay policies; the YouTube player
   handles normal playback and playlist advancement thereafter.
4. The player reports `PLAYING`, `PAUSED`, `ENDED`, and error events to the
   local server. The queue marks tracks `PLAYED` only on `ENDED`; embed errors
   mark the affected track `FAILED` and the page attempts the next item.
5. The user can pause/resume with the YouTube controls or stop the queue from
   the local player page. Ctrl+C stops the CLI's state monitoring.
6. The CLI prints the final state of each track.

The application does not bypass ads, authentication, regional restrictions,
or YouTube embed restrictions. A video that cannot be embedded is reported as
failed; the app does not extract or proxy its media stream.

## YouTube account session

Candidate searches use an isolated browser context and do not reuse account
cookies. The player page uses YouTube's embedded player; videos that require a
signed-in top-level YouTube session may not be playable there.

## Local inference and configuration

Ollama receives image data at the configured local endpoint. The model output is
treated as untrusted data and validated before it reaches the queue or browser.
The model cannot generate or execute shell commands or Python code.

See the repository README for installation, Ollama model setup, environment
variables, and CLI usage.
