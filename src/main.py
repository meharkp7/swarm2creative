import pygame
from engine import Agent, WIDTH, HEIGHT
import engine

EXPORT_WIDTH = 800
EXPORT_HEIGHT = 600
ART_STYLE = "mandala"
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SRCALPHA)
render_surface = pygame.Surface((EXPORT_WIDTH, EXPORT_HEIGHT), pygame.SRCALPHA)
pygame.display.set_caption("Swarm Engine - Basic Movement")
clock = pygame.time.Clock()
save_next = False
agents = [Agent() for _ in range(50)]
time = 0
running = True
while running:
    fade_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    fade_surface.fill((0,0,0,20))
    if ART_STYLE == "geometric":
        render_surface.blit(fade_surface, (0,0))
    elif ART_STYLE == "mandala":
        screen.blit(fade_surface, (0,0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                engine.ART_MODE = "calm"
                print("Mode → CALM")

            if event.key == pygame.K_2:
                engine.ART_MODE = "chaos"
                print("Mode → CHAOS")

            if event.key == pygame.K_3:
                engine.ART_MODE = "galaxy"
                print("Mode → GALAXY")

            if event.key == pygame.K_4:
                engine.ART_MODE = "flow"
                print("Mode → FLOW")

            if event.key == pygame.K_5:
                engine.ART_MODE = "composition"
                print("Mode → COMPOSITION")
            
            if event.key == pygame.K_q:
                engine.EMOTION = "calm"
                print("Emotion → CALM")

            if event.key == pygame.K_w:
                engine.EMOTION = "anxiety"
                print("Emotion → ANXIETY")

            if event.key == pygame.K_e:
                engine.EMOTION = "joy"
                print("Emotion → JOY")

            if event.key == pygame.K_s:
                save_next = True
                print("Saving…")
            
            if event.key == pygame.K_g:
                ART_STYLE = "geometric"
                print("STYLE → GEOMETRIC")

            if event.key == pygame.K_m:
                ART_STYLE = "mandala"
                print("STYLE → MANDALA")

    for agent in agents:
        agent.apply_behaviors(agents, time)
        agent.update()
        agent.draw(render_surface)

    scaled = pygame.transform.smoothscale(render_surface, (WIDTH, HEIGHT))
    screen.blit(scaled, (0,0))

    if save_next:
        pygame.image.save(render_surface, "art.png")
        print("Saved Art!")
        save_next = False

    pygame.display.flip()
    clock.tick(80)
    time += 0.005
    keys = pygame.key.get_pressed()
    if keys[pygame.K_s]:
        pygame.image.save(render_surface, "art.png")
        print("Saved Art!")

pygame.quit()