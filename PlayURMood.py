import tkinter as tk
from tkinter import ttk, scrolledtext
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import threading
import speech_recognition as sr
import re
import time
import platform

# Spotify Credentials
SPOTIFY_CLIENT_ID = 'SPOTIFY_CLIENT_ID'
SPOTIFY_CLIENT_SECRET = 'SPOTIFY_CLIENT_SECRET'
SPOTIFY_REDIRECT_URI = 'http://127.0.0.1:8080/callback'
SCOPE = 'playlist-modify-public playlist-modify-private user-read-playback-state user-modify-playback-state'
CACHE_PATH = 'spotify_token.cache'

class PlayURMoodApp:
    def __init__(self, root, sp):
        self.root = root
        self.root.title("🎃 Boo! PlayURMood - Spooky Music Assistant 🎃")
        self.root.geometry("600x700")
        self.root.configure(bg='orange')  # Goofy Halloween background

        self.sp = sp
        self.current_playlist_id = None
        self.voice_active = False
        self.voice_thread = None

        # Check if speech is supported (disable on macOS due to known crashes)
        self.speech_enabled = platform.system() != 'Darwin'

        self.recognizer = sr.Recognizer()

        self.setup_gui()
        self.enable_buttons()
        if not self.speech_enabled:
            self.log_message("Voice output disabled on macOS to prevent crashes. Voice input still available.")
        self.log_message("Spotify authentication successful. 🎃 Ready for some spooky tunes! 🎃")

    def setup_gui(self):
        # Halloween-themed style
        style = ttk.Style()
        style.configure('TLabel', background='orange', foreground='black', font=('Comic Sans MS', 10, 'bold'))  # Goofy font
        style.configure('TButton', background='black', foreground='orange', font=('Comic Sans MS', 10, 'bold'))
        style.configure('TEntry', font=('Comic Sans MS', 10))

        ttk.Label(self.root, text="👻 User Name (Ghostly Edition):").grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
        self.user_name_entry = ttk.Entry(self.root)
        self.user_name_entry.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(self.root, text="🦇 Mood (Bat-tastic!):").grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)
        self.mood_entry = ttk.Entry(self.root)
        self.mood_entry.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(self.root, text="🎃 Artist (Pumpkin Optional):").grid(row=2, column=0, padx=10, pady=5, sticky=tk.W)
        self.artist_entry = ttk.Entry(self.root)
        self.artist_entry.grid(row=2, column=1, padx=10, pady=5)

        ttk.Label(self.root, text="🕸️ Language (Web of Words):").grid(row=3, column=0, padx=10, pady=5, sticky=tk.W)
        self.language_entry = ttk.Entry(self.root)
        self.language_entry.grid(row=3, column=1, padx=10, pady=5)

        ttk.Label(self.root, text="🍬 Playlist Size (Trick or Treat?):").grid(row=4, column=0, padx=10, pady=5, sticky=tk.W)
        self.size_entry = ttk.Entry(self.root)
        self.size_entry.insert(0, "10")
        self.size_entry.grid(row=4, column=1, padx=10, pady=5)

        # Buttons with spooky names
        self.create_playlist_btn = ttk.Button(self.root, text="🧙‍♀️ Brew Playlist (Witch's Brew!)")
        self.create_playlist_btn.config(command=self.create_playlist)
        self.create_playlist_btn.grid(row=5, column=0, padx=10, pady=10)
        self.play_playlist_btn = ttk.Button(self.root, text="🎶 Haunt Playlist (Ghostly Groove!)")
        self.play_playlist_btn.config(command=self.play_playlist)
        self.play_playlist_btn.grid(row=5, column=1, padx=10, pady=10)
        self.voice_mode_btn = ttk.Button(self.root, text="🗣️ Toggle Voice Mode (Spooky Speak!)")
        self.voice_mode_btn.config(command=self.toggle_voice_mode)
        self.voice_mode_btn.grid(row=6, column=0, columnspan=2, padx=10, pady=10)

        # Playback controls with Halloween flair
        ttk.Label(self.root, text="🎭 Playback Controls (Monster Mash!):").grid(row=7, column=0, columnspan=2)
        self.play_btn = ttk.Button(self.root, text="▶️ Play (Rise from the Grave!)")
        self.play_btn.config(command=lambda: self.run_thread(self.play))
        self.play_btn.grid(row=8, column=0, padx=5, pady=5)
        self.pause_btn = ttk.Button(self.root, text="⏸️ Pause (Zombie Freeze!)")
        self.pause_btn.config(command=lambda: self.run_thread(self.pause))
        self.pause_btn.grid(row=8, column=1, padx=5, pady=5)
        self.next_btn = ttk.Button(self.root, text="⏭️ Next (Boo Next!)")
        self.next_btn.config(command=lambda: self.run_thread(self.next_track))
        self.next_btn.grid(row=9, column=0, padx=5, pady=5)
        self.prev_btn = ttk.Button(self.root, text="⏮️ Previous (Back to the Crypt!)")
        self.prev_btn.config(command=lambda: self.run_thread(self.previous_track))
        self.prev_btn.grid(row=9, column=1, padx=5, pady=5)
        self.shuffle_btn = ttk.Button(self.root, text="🔀 Shuffle (Witch's Cauldron Mix!)")
        self.shuffle_btn.config(command=lambda: self.run_thread(self.toggle_shuffle))
        self.shuffle_btn.grid(row=10, column=0, padx=5, pady=5)
        self.repeat_btn = ttk.Button(self.root, text="🔁 Repeat (Eternal Loop of Doom!)")
        self.repeat_btn.config(command=lambda: self.run_thread(self.toggle_repeat))
        self.repeat_btn.grid(row=10, column=1, padx=5, pady=5)

        # Log area with spooky theme
        self.log_text = scrolledtext.ScrolledText(self.root, width=70, height=15, bg='black', fg='orange', font=('Courier', 10))
        self.log_text.grid(row=11, column=0, columnspan=2, padx=10, pady=10)
        self.status_label = ttk.Label(self.root, text="🎃 Spotify: Ready for Halloween Hits! 🎃")
        self.status_label.grid(row=12, column=0, columnspan=2)

    def log_message(self, message):
        ts = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{ts}] {message}\n")
        self.log_text.see(tk.END)

    # Speech function - disabled on macOS
    def speak_feedback(self, text):
        if not self.speech_enabled:
            return  # No speech on macOS
        # If we wanted to enable speech on other platforms, we could add pyttsx3 here, but for now, skip
        pass  # Speech is disabled to prevent crashes

    def enable_buttons(self):
        for btn in [self.create_playlist_btn, self.play_playlist_btn, self.play_btn,
                    self.pause_btn, self.next_btn, self.prev_btn, self.shuffle_btn, self.repeat_btn]:
            btn.config(state=tk.NORMAL)

    def run_thread(self, func, *args):
        threading.Thread(target=func, args=args, daemon=True).start()

    # Spotify actions (same as before, all functions threaded)
    def create_playlist(self):
        self.run_thread(self._create_playlist_thread)

    def _create_playlist_thread(self):
        user_name = self.user_name_entry.get().strip() or "Guest"
        mood = self.mood_entry.get().strip() or "popular"
        artist = self.artist_entry.get().strip()
        language = self.language_entry.get().strip()
        try:
            size = int(self.size_entry.get())
        except ValueError:
            self.log_message("Invalid playlist size.")
            return

        playlist_name = f"{user_name}_{mood}_Mood"
        try:
            playlist = self.sp.user_playlist_create(user=self.sp.current_user()['id'], name=playlist_name, public=False)
            self.current_playlist_id = playlist['id']
            self.log_message(f"Playlist '{playlist_name}' created.")
            query = f"{mood} {artist} {language}".strip()
            results = self.sp.search(q=query, type='track', limit=size)
            track_uris = [t['uri'] for t in results['tracks']['items']]
            if track_uris:
                self.sp.playlist_add_items(self.current_playlist_id, track_uris)
                self.log_message(f"Added {len(track_uris)} tracks.")
            else:
                self.log_message("No tracks found.")
        except Exception as e:
            self.log_message(f"Error creating playlist: {e}")

    def play_playlist(self):
        self.run_thread(self._play_playlist_thread)

    def _play_playlist_thread(self):
        if not self.current_playlist_id:
            self.log_message("No playlist to play.")
            return
        try:
            self.sp.start_playback(context_uri=f"spotify:playlist:{self.current_playlist_id}")
            self.log_message("Playing playlist.")
        except Exception as e:
            self.log_message(f"Error playing playlist: {e}")

    # Playback controls
    def play(self):
        self._spotify_call(self.sp.start_playback, "Playback started")
    def pause(self):
        self._spotify_call(self.sp.pause_playback, "Playback paused")
    def next_track(self):
        self._spotify_call(self.sp.next_track, "Skipped to next track")
    def previous_track(self):
        self._spotify_call(self.sp.previous_track, "Skipped to previous track")
    def toggle_shuffle(self):
        try:
            current = self.sp.current_playback()
            new_state = not current['shuffle_state'] if current else True
            self.sp.shuffle(new_state)
            self.log_message(f"Shuffle {'on' if new_state else 'off'}.")
        except Exception as e:
            self.log_message(f"Shuffle error: {e}")
    def toggle_repeat(self):
        try:
            states = ['off', 'track', 'context']
            current = self.sp.current_playback()
            current_state = current['repeat_state'] if current else 'off'
            next_state = states[(states.index(current_state)+1)%3]
            self.sp.repeat(next_state)
            self.log_message(f"Repeat: {next_state}")
        except Exception as e:
            self.log_message(f"Repeat error: {e}")
    def _spotify_call(self, func, feedback_text):
        try:
            func()
            self.log_message(feedback_text)
        except Exception as e:
            self.log_message(f"{feedback_text} error: {e}")

    # Voice commands
    def toggle_voice_mode(self):
        if self.voice_active:
            self.voice_active = False
            self.log_message("Voice mode disabled.")
        else:
            self.voice_active = True
            self.voice_thread = threading.Thread(target=self.voice_loop, daemon=True)
            self.voice_thread.start()
            self.log_message("Voice mode enabled. Say commands like 'create 10 happy songs by Taylor Swift'.")

    def voice_loop(self):
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            while self.voice_active:
                try:
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                    command = self.recognizer.recognize_google(audio).lower()
                    self.process_voice_command(command)
                except (sr.WaitTimeoutError, sr.UnknownValueError):
                    continue
                except Exception as e:
                    self.log_message(f"Voice error: {e}")

    def process_voice_command(self, command):
        self.log_message(f"Voice command: {command}")
        if "create" in command:
            match = re.search(r'create (\d+) (.+?) songs(?: by (.+?))?(?: in (.+?))?$', command)
            if match:
                size, mood, artist, language = match.groups()
                self.user_name_entry.delete(0, tk.END)
                self.user_name_entry.insert(0, "VoiceUser")
                self.mood_entry.delete(0, tk.END)
                self.mood_entry.insert(0, mood.strip())
                self.artist_entry.delete(0, tk.END)
                if artist: self.artist_entry.insert(0, artist.strip())
                self.language_entry.delete(0, tk.END)
                if language: self.language_entry.insert(0, language.strip())
                self.size_entry.delete(0, tk.END)
                self.size_entry.insert(0, size)
                self.create_playlist()
        elif "play playlist" in command:
            self.play_playlist()
        elif "pause" in command:
            self.pause()
        elif "resume" in command:
            self.play()
        elif "next" in command:
            self.next_track()
        elif "previous" in command:
            self.previous_track()
        elif "shuffle on" in command:
            self.sp.shuffle(True)
            self.log_message("Shuffle on.")
        elif "shuffle off" in command:
            self.sp.shuffle(False)
            self.log_message("Shuffle off.")
        elif "repeat playlist" in command:
            self.sp.repeat('context')
            self.log_message("Repeat playlist.")
        elif "repeat track" in command:
            self.sp.repeat('track')
            self.log_message("Repeat track.")
        elif "repeat off" in command:
            self.sp.repeat('off')
            self.log_message("Repeat off.")
        elif "stop voice" in command:
            self.toggle_voice_mode()

def main():
    try:
        # Step 1: Authenticate Spotify
        auth_manager = SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope=SCOPE,
            cache_path=CACHE_PATH,
            open_browser=True
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)
    except Exception as e:
        print(f"Spotify authentication failed: {e}")
        return  # Exit if auth fails

    # Step 2: Start GUI after authentication
    root = tk.Tk()
    app = PlayURMoodApp(root, sp)
    root.mainloop()

if __name__ == "__main__":
    main()
