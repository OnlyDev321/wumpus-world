import os
import pygame


class SoundManager:
    """
    Manages loading, volume balance, and playback of game audio effects.
    Safely degrades if audio device is unavailable or files are missing.
    """

    def __init__(self, sound_dir="assets/sounds"):
        self.sounds = {}
        self.sound_dir = sound_dir
        self.is_enabled = True

        # Check if mixer is initialized
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception as e:
                print(f"[SoundManager] Failed to initialize mixer: {e}")
                self.is_enabled = False
                return

        self._load_sounds()

    def _load_sounds(self):
        """Loads all sound effects with configured volume levels."""
        sound_configs = {
            "breeze": ("breeze.wav", 0.6),
            "stench": ("stench.wav", 0.7),
            "glitter": ("glitter.wav", 0.8),
            "scream": ("scream.wav", 1.0),
            "door": ("door.wav", 0.9),
            "pit": ("pit.wav", 0.9),
            "wumpus": ("wumpus.wav", 0.95),
            "gold": ("gold.wav", 0.85),
        }

        for key, (filename, volume) in sound_configs.items():
            path = os.path.join(self.sound_dir, filename)
            if os.path.exists(path):
                try:
                    snd = pygame.mixer.Sound(path)
                    snd.set_volume(volume)
                    self.sounds[key] = snd
                except Exception as e:
                    print(f"[SoundManager] Error loading {path}: {e}")
            else:
                print(f"[SoundManager] Warning: Audio file not found: {path}")

    def play(self, sound_name):
        """Plays a specific sound by key."""
        if not self.is_enabled:
            return
        snd = self.sounds.get(sound_name)
        if snd:
            try:
                snd.play()
            except Exception:
                pass

    def stop(self, sound_name):
        """Stops a specific sound by key."""
        if not self.is_enabled:
            return
        snd = self.sounds.get(sound_name)
        if snd:
            try:
                snd.stop()
            except Exception:
                pass

    def stop_percepts(self):
        """Stops ongoing ambient percept sounds to prevent overlap in fast auto mode."""
        for key in ("breeze", "stench", "glitter"):
            self.stop(key)

    def play_percepts(self, percepts):
        """
        Triggers corresponding audio cues for current percepts:
        - breeze -> breeze.wav
        - stench -> stench.wav
        - glitter -> glitter.wav
        """
        if not self.is_enabled or not percepts:
            return

        # Stop previous percept sounds so steps don't stack excessively
        self.stop_percepts()

        if "breeze" in percepts:
            self.play("breeze")
        if "stench" in percepts:
            self.play("stench")
        if "glitter" in percepts:
            self.play("glitter")

    def stop_all(self):
        """Stops all playing sounds on mixer."""
        if not self.is_enabled:
            return
        try:
            pygame.mixer.stop()
        except Exception:
            pass
