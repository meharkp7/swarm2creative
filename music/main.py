import pygame
from engine import Agent, WIDTH, HEIGHT, NUM_AGENTS
from data_layer import SwarmStateBuffer, EventLogger

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Swarm Intelligence Engine")

clock = pygame.time.Clock()

# ---------------- Data Layer Initialization ----------------
swarm_buffer = SwarmStateBuffer()
event_logger = EventLogger()
frame_count = 0

# ---------------- Agents ----------------
agents = [Agent() for _ in range(NUM_AGENTS)]

running = True
while running:
    clock.tick(60)  # FPS
    frame_count += 1

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill((0, 0, 0))  # black background

    for agent in agents:
        agent.apply_behaviors(agents)
        agent.update()
        agent.edges()

        # draw agent
        pygame.draw.circle(
            screen,
            (255, 255, 255),
            agent.pos,
            2
        )

    # ---------------- Log Data Layer ----------------
    swarm_buffer.log_frame(agents)

    # Example: log collisions if agents get too close
    for i, a1 in enumerate(agents):
        for j, a2 in enumerate(agents[i+1:], start=i+1):
            if a1.pos.distance_to(a2.pos) < 5:  # collision threshold
                event_logger.log_event(frame_count, "collision", {"agents": (i, j)})

    # -------------------------------------------------

    pygame.display.flip()

pygame.quit()

# ---------------- Optional: Save / inspect logged data ----------------
print("Total frames logged:", swarm_buffer.total_frames())
print("Sample events logged:", event_logger.get_events()[:5])  # print first 5 events

from pathlib import Path
from music_mapper import SwarmMusicMapper

# --------------------------------
# Initialize music system
# --------------------------------
music = SwarmMusicMapper()

for frame in swarm_buffer.frames:
    music.add_frame(frame)

# --------------------------------
# Resolve output path safely
# --------------------------------
BASE_DIR = Path(__file__).parent           # music/
OUTPUT_DIR = BASE_DIR / "outputs"          # music/outputs/
OUTPUT_DIR.mkdir(exist_ok=True)

music_file = OUTPUT_DIR / "swarm_music.mid"

# --------------------------------
# Save MIDI
# --------------------------------
music.save(music_file)

print("🎼 swarm_music.mid generated in music/outputs/")
