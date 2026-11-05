"""
Setup:
    pip install spotipy
    export SPOTIPY_CLIENT_ID="..."
    export SPOTIPY_CLIENT_SECRET="..."
    export SPOTIPY_REDIRECT_URI="http://127.0.0.1:8888/callback"
    python spotify_type_game.py

Requirements:
    - A Spotify app from https://developer.spotify.com/dashboard
      (add the redirect URI above to the app's settings)
    - Spotify Premium (the Web API can only control playback for Premium)
    - Spotify open and active on some device (phone, desktop app, web player)
"""

import random
import re
import sys
import time
import unicodedata
from difflib import SequenceMatcher

import spotipy
from spotipy.oauth2 import SpotifyOAuth

SCOPE = (
    "playlist-read-private "
    "playlist-read-collaborative "
    "user-read-playback-state "
    "user-modify-playback-state"
)

CORRECT_THRESHOLD = 0.75  # close guesses = correct


def strip_accents(text: str) -> str: # standardizes accents
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )


def normalize(text: str) -> str: # standardizes text
    text = strip_accents(text).lower().replace("&", "and")
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def title_variants(title: str) -> set[str]: # creates acceptable titles
    variants = {normalize(title)}

    no_brackets = re.sub(r"[\(\[].*?[\)\]]", "", title).strip()
    variants.add(normalize(no_brackets))

    before_dash = re.split(r"\s+-\s+", title, maxsplit=1)[0]
    variants.add(normalize(before_dash))
    variants.add(normalize(re.sub(r"[\(\[].*?[\)\]]", "", before_dash)))

    variants.discard("")
    return variants


def grade_guess(guess: str, title: str) -> tuple[str, float]: # is your guess correct?
    g = normalize(guess)
    if not g:
        return "WRONG", 0.0

    best = max(SequenceMatcher(None, g, v).ratio() for v in title_variants(title))

    if best >= CORRECT_THRESHOLD:
        return "CORRECT", best
    return "WRONG", best

def get_all_playlists(sp: spotipy.Spotify) -> list[dict]:
    playlists, offset = [], 0
    while True:
        page = sp.current_user_playlists(limit=50, offset=offset)
        items = [p for p in page["items"] if p]
        playlists.extend(items)
        if page.get("next") is None:
            break
        offset += 50
    return playlists


def get_playlist_tracks(sp: spotipy.Spotify, playlist_id: str) -> list[dict]:
    tracks, offset = [], 0
    while True:
        page = sp.playlist_items(
            playlist_id,
            limit=100,
            offset=offset,
            additional_types=("track",),
        )
        for item in page["items"]:
            # Newer API responses may call this "item" instead of "track".
            t = item.get("track") or item.get("item")
            if not t or t.get("is_local") or not t.get("uri") or t.get("type") != "track":
                continue
            tracks.append(
                {
                    "name": t["name"],
                    "artists": ", ".join(a["name"] for a in t["artists"]),
                    "uri": t["uri"],
                }
            )
        if page.get("next") is None:
            break
        offset += 100
    return tracks


def pick_device(sp: spotipy.Spotify) -> str:
    while True:
        devices = sp.devices().get("devices", [])
        if not devices:
            input(
                "\nNo Spotify devices found. Open Spotify on your phone/desktop/web, "
                "play anything for a second, then press Enter to retry..."
            )
            continue

        for d in devices:
            if d.get("is_active"):
                return d["id"]

        if len(devices) == 1:
            return devices[0]["id"]

        print("\nAvailable devices:")
        for i, d in enumerate(devices, 1):
            print(f"  {i}. {d['name']} ({d['type']})")
        choice = input("Pick a device number: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(devices):
            return devices[int(choice) - 1]["id"]
        print("Invalid choice.")


def choose_playlist(playlists: list[dict]) -> dict:
    print("\nYour playlists:\n")
    for i, p in enumerate(playlists, 1):
        total = p.get("tracks", {}).get("total") or p.get("items", {}).get("total", "?")
        print(f"  {i:>3}. {p['name']}  ({total} tracks)")
    while True:
        choice = input("\nChoose a playlist number: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(playlists):
            return playlists[int(choice) - 1]
        print("Invalid choice, try again.")

def play_game(sp: spotipy.Spotify, tracks: list[dict], device_id: str) -> list[dict]:
    results = []
    random.shuffle(tracks)

    print("\nType the song title and press Enter.")
    print('Commands: "skip" to count a song as wrong, "exit" to finish.\n')

    for n, track in enumerate(tracks, 1):
        try:
            sp.start_playback(device_id=device_id, uris=[track["uri"]])
        except spotipy.SpotifyException as e:
            print(f"Couldn't play '{track['name']}' ({e.reason or e}). Skipping.")
            continue

        start = time.perf_counter()
        guess = input(f"[{n}/{len(tracks)}] Song title > ")
        elapsed = time.perf_counter() - start
        cmd = guess.strip().lower()

        if cmd == "exit":
            break
        skipped = cmd == "skip"
        grade, score = ("WRONG", 0.0) if skipped else grade_guess(guess, track["name"])
        results.append(
            {
                "title": track["name"],
                "artists": track["artists"],
                "guess": guess.strip(),
                "grade": grade,
                "similarity": score,
                "time": elapsed,
            }
        )

        if skipped:
            print(f"  Skipped (counts as wrong). It was: {track['name']} - {track['artists']}")
        elif grade == "CORRECT":
            print(f"  Correct! ({elapsed:.2f}s)")
        else:
            print(f"  Nope ({score:.0%} match). It was: {track['name']} - {track['artists']}")
        print()

    return results


def show_summary(results: list[dict]) -> None:
    print("\n" + "=" * 50)
    print("ROUND SUMMARY")
    print("=" * 50)

    if not results:
        print("No guesses made this round.")
        return

    correct = sum(r["grade"] == "CORRECT" for r in results)
    wrong = sum(r["grade"] == "WRONG" for r in results)
    avg_time = sum(r["time"] for r in results) / len(results)

    print(f"Songs attempted: {len(results)}  (correct: {correct}, wrong: {wrong})")
    print(f"Accuracy: {correct / len(results):.1%}")
    print(f"Average time across all attempts (including skips): {avg_time:.2f}s")

    # Only correct answers count for "fastest"; skips are wrong.
    valid = [r for r in results if r["grade"] == "CORRECT"]
    if valid:
        best = min(valid, key=lambda r: r["time"])
        print(f"Fastest time: {best['time']:.2f}s  ->  {best['title']} - {best['artists']}")
    else:
        print("Fastest time: n/a (no correct guesses)")


def main() -> None:
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPE))
        me = sp.current_user()
    except Exception as e:
        sys.exit(
            f"Could not authenticate with Spotify: {e}\n"
            "Check SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET and SPOTIPY_REDIRECT_URI."
        )

    print(f"Logged in as {me.get('display_name') or me['id']}")

    playlists = get_all_playlists(sp)
    if not playlists:
        sys.exit("No playlists found on your account.")

    playlist = choose_playlist(playlists)
    tracks = get_playlist_tracks(sp, playlist["id"])
    if not tracks:
        sys.exit("That playlist has no playable tracks.")
    print(f"\nLoaded {len(tracks)} tracks from '{playlist['name']}'.")

    device_id = pick_device(sp)
    results = []
    try:
        results = play_game(sp, tracks, device_id)
    except (KeyboardInterrupt, EOFError):
        print("\nInterrupted.")
    finally:
        try:
            sp.pause_playback(device_id=device_id)
        except Exception:
            pass

    show_summary(results)


if __name__ == "__main__":
    main()
