# music_mapper.py
import math
from mido import Message, MidiFile, MidiTrack, MetaMessage


WIDTH = 900  # same as engine
SCALE = [60, 62, 64, 65, 67, 69, 71]  # C Major


class SwarmMusicMapper:
    def __init__(self):
        self.mid = MidiFile()

        # ---- MELODY TRACK ----
        self.melody = MidiTrack()
        self.mid.tracks.append(self.melody)
        self.melody.append(Message('program_change', program=48, time=0))

        # ---- BASS TRACK ----
        self.bass = MidiTrack()
        self.mid.tracks.append(self.bass)
        self.bass.append(Message('program_change', program=32, time=0))

        self.last_pitch = None
        self.frame_count = 0

        # ---- TEMPO ----
        self.base_tempo = 500000  # 120 BPM
        self.current_tempo = self.base_tempo

        # set initial tempo (must be on track 0)
        self.melody.append(
            MetaMessage('set_tempo', tempo=self.base_tempo, time=0)
        )

    # ---------------- UTILS ----------------

    def speed(self, vel):
        return math.sqrt(vel[0] ** 2 + vel[1] ** 2)

    def compute_swarm_energy(self, frame):
        return sum(self.speed(a['vel']) for a in frame) / len(frame)

    def energy_to_tempo(self, energy):
        bpm = 60 + energy * 20
        bpm = max(60, min(140, bpm))
        return int(60_000_000 / bpm)

    # ---------------- MELODY ----------------

    def melody_notes(self, frame):
        notes = []
        for agent in frame:
            x, _ = agent['pos']
            vel = agent['vel']

            idx = int((x / WIDTH) * len(SCALE))
            idx = min(idx, len(SCALE) - 1)
            target = SCALE[idx]

            if self.last_pitch is None:
                pitch = target
            else:
                pitch = int(self.last_pitch * 0.7 + target * 0.3)

            self.last_pitch = pitch

            volume = int(min(127, self.speed(vel) * 40))
            notes.append((pitch, volume))

        return sorted(notes, key=lambda n: n[1], reverse=True)

    # ---------------- BASS ----------------

    def bass_note(self, frame):
        avg_x = sum(a['pos'][0] for a in frame) / len(frame)
        idx = int((avg_x / WIDTH) * len(SCALE))
        idx = min(idx, len(SCALE) - 1)

        # Bass = root note two octaves down
        return SCALE[idx] - 24

    # ---------------- FRAME ----------------

    def add_frame(self, frame):
        self.frame_count += 1

        # ---- TEMPO ----
        energy = self.compute_swarm_energy(frame)
        tempo = self.energy_to_tempo(energy)

        if tempo != self.current_tempo:
            self.melody.append(
                MetaMessage('set_tempo', tempo=tempo, time=0)
            )
            self.current_tempo = tempo

        duration = int(100 + energy * 30)

        # ---- MELODY (every frame) ----
        melody = self.melody_notes(frame)[:3]
        for pitch, volume in melody:
            self.melody.append(
                Message('note_on', note=pitch, velocity=volume, time=0)
            )
            self.melody.append(
                Message('note_off', note=pitch, velocity=64, time=duration)
            )

        # ---- BASS (every 8 frames) ----
        if self.frame_count % 8 == 0:
            bass_pitch = self.bass_note(frame)

            self.bass.append(
                Message('note_on', note=bass_pitch, velocity=70, time=0)
            )
            self.bass.append(
                Message('note_off', note=bass_pitch, velocity=64, time=duration * 4)
            )

    def save(self, filename="swarm_music.mid"):
        self.mid.save(filename)
