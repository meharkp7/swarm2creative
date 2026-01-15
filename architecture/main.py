import pygame
from engine import Agent, WIDTH, HEIGHT, ARCHITECTURE_MODE
import engine

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Swarm Engine - Architecture Emergence")
clock = pygame.time.Clock()
architecture_surface = None
ANCHOR_THRESHOLD = 12
agents = [Agent() for _ in range(50)]
ARCHITECTURE_COMMITTED = False
ARCH_TIME = pygame.time.get_ticks()
running = True

engine.SHOW_CONNECTIVITY = False
engine.SHOW_HIERARCHY = False
engine.SHOW_DOORS = False

print("=" * 60)
print("🏛️  SWARM ARCHITECTURE ENGINE")
print("=" * 60)
print("Controls:")
print("  C - Toggle Connectivity Graph")
print("  H - Toggle Circulation Hierarchy")
print("  D - Toggle Door Information")
print("  P - Export Architecture JSON")
print("=" * 60)

while running:
    screen.fill((0, 0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                engine.export_architecture(agents)
            
            if event.key == pygame.K_c:
                engine.SHOW_CONNECTIVITY = not engine.SHOW_CONNECTIVITY
                state = "ON" if engine.SHOW_CONNECTIVITY else "OFF"
                print(f"🔗 Connectivity view: {state}")
            
            if event.key == pygame.K_h:
                engine.SHOW_HIERARCHY = not engine.SHOW_HIERARCHY
                state = "ON" if engine.SHOW_HIERARCHY else "OFF"
                print(f"🏗️  Hierarchy view: {state}")
            
            if event.key == pygame.K_d:
                engine.SHOW_DOORS = not engine.SHOW_DOORS
                state = "ON" if engine.SHOW_DOORS else "OFF"
                print(f"🚪 Door info: {state}")

    if not ARCHITECTURE_COMMITTED:
        for agent in agents:
            agent.apply_behaviors(agents)
            agent.update(agents)

        anchor_count = sum(1 for a in agents if a.is_anchor)

        if anchor_count >= ANCHOR_THRESHOLD and not ARCHITECTURE_COMMITTED:
            ARCHITECTURE_COMMITTED = True

            engine.commit_architecture(agents)
            architecture_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            engine.draw_architecture(architecture_surface)

            engine.ARCHITECTURE_MODE = True
            engine.ARCHITECTURE["agents"] = agents
            ARCH_TIME = pygame.time.get_ticks()
            
            print("\n" + "=" * 60)
            print("🏛️  ARCHITECTURE COMMITTED")
            print("=" * 60)
        
        if (
            engine.ARCHITECTURE_MODE
            and pygame.time.get_ticks() % 4000 < 16
        ):
            engine.evolve_rooms()
            engine.decay_room_memory()

    else:
        for agent in agents:
            agent.apply_behaviors(agents)
            agent.update(agents)

        if architecture_surface:
            screen.blit(architecture_surface, (0, 0))
    
    if (
        engine.ARCHITECTURE_MODE
        and pygame.time.get_ticks() - ARCH_TIME > 10000
        and pygame.time.get_ticks() % 3000 < 16
    ):
        engine.smart_prune_rooms(min_hits=120)
        engine.refresh_architecture_surface(architecture_surface)
    
    if engine.ARCHITECTURE_MODE and engine.needs_visual_refresh():
        engine.refresh_architecture_surface(architecture_surface)

    for agent in agents:
        agent.draw(screen)

    if ARCHITECTURE_COMMITTED:
        if engine.SHOW_CONNECTIVITY:
            engine.draw_connectivity_debug(screen)
        
        if engine.SHOW_HIERARCHY:
            engine.draw_circulation_hierarchy(screen)
        
        if engine.SHOW_DOORS:
            engine.draw_door_info(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
print("\n🏛️  Architecture engine closed")