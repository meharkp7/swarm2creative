import pygame
from engine import Agent, WIDTH, HEIGHT

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Swarm Engine - Basic Movement")
clock = pygame.time.Clock()

agents = [Agent() for _ in range(50)]

running = True
while running:
    screen.fill((0, 0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    for agent in agents:
        agent.apply_behaviors(agents)
        agent.update()
        agent.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()