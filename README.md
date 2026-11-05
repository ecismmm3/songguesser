# songguesser
Do you know your playlists?

I'm a big music fan, so I created a way to test my music knowledge. This program allows you to shuffle through your playlists in Spotify, and you must type the title as fast as you can. For Windows users only.

## Requirements

- Python **3.9 or newer**.
- Spotify Premium account
- A Spotify developer app with a Client ID, Client Secret, and registered redirect URI.
- Spotify application open on computer, phone, or web player.
- Internet connection

## Setup

### 1. Configure Spotify app

1. Sign in at [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Create an app.
3. In its settings, add this redirect URI and save:

   ```text
   http://127.0.0.1:8888/callback
   ```

4. Copy the app's **Client ID** and **Client Secret** for the environment variables below.

### 2. Install dependency

Open the folder containing `song_guesser.py` in VS Code, and open a new Terminal.

For Windows PowerShell, create a virtual environment and install Spotipy:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install spotipy
```

### 3. Set your credentials

In the **same terminal**, replace the placeholders with your spotify ID, secret, and URI, and run:

```powershell
$env:SPOTIPY_CLIENT_ID = "YOUR_CLIENT_ID"
$env:SPOTIPY_CLIENT_SECRET = "YOUR_CLIENT_SECRET"
$env:SPOTIPY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
```

**NOTE: These commands must be reentered if you open a new terminal.**

### 4. Start the game

1. Open Spotify and play a song briefly for the program to detect spotify.
2. Run (`python songguesser.py` in VSCode):

   ```powershell
   .\.venv\Scripts\python.exe spotify_type_game.py
   ```

3. On the first run, approve Spotify access in the browser. If prompted by Spotipy, paste the redirected URL into the terminal.
4. Choose a playlist by its number.
5. If prompted, choose a playback device.

## Usage

| Input | Action |
|---|---|
| Song title | Grade the answer and continue |
| `skip` | Count the song as wrong, reveal the title, and continue |
| `exit` | End the round and display your statistics |

Use `exit` to finish the round and view your the round summary described below.

## Scoring

- **Correct:** The best normalized title match has a similarity of at least **0.75**.
- **Wrong:** A guess below the threshold, an empty guess, or a skipped song
- **Average time per song:** Average time spent across all attempts (correct guesses, wrong guesses, and manual skips).
- **Fastest time:** The quickest you typed a correct guess.

Title matching normalizes case, accents, punctuation, and spaces, brackets, and dashes, so you do not have to worry about features or other special text.

Example:

```text
Official title: Example Song (feat. Artist)
Accepted form: Example Song

Official title: Example Song - Remastered 2011
Accepted form: Example Song
```

Similarity uses Python's `SequenceMatcher`, a text comparison tool.

## Configuration

You can change this constant near the top of `songguesser.py` to adjust strictness (higher = more strict):

```python
CORRECT_THRESHOLD = 0.75
```
