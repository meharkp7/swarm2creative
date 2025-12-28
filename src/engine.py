import pygame
import random

WIDTH = 800
HEIGHT = 600

def get_neighbors(agent, agents, radius):
    neighbors = []
    for other in agents:
        if other is agent:
            continue
        if agent.pos.distance_to(other.pos) < radius:
            neighbors.append(other)
    return neighbors

def alignment(agent, neighbors, strength=0.05):
    if not neighbors:
        return pygame.Vector2(0, 0)

    avg_vel = pygame.Vector2(0, 0)
    for other in neighbors:
        avg_vel += other.vel

    avg_vel /= len(neighbors)

    steer = avg_vel - agent.vel
    steer *= strength
    return steer

def cohesion(agent, neighbors, strength=0.01):
    if not neighbors:
        return pygame.Vector2(0, 0)

    center = pygame.Vector2(0, 0)
    for other in neighbors:
        center += other.pos

    center /= len(neighbors)

    steer = center - agent.pos
    steer *= strength
    return steer

def separation(agent, neighbors, desired_distance=25, strength=0.15):
    if not neighbors:
        return pygame.Vector2(0, 0)

    steer = pygame.Vector2(0, 0)
    total = 0

    for other in neighbors:
        dist = agent.pos.distance_to(other.pos)
        if dist < desired_distance and dist > 0:
            diff = agent.pos - other.pos
            diff /= dist
            steer += diff
            total += 1

    if total > 0:
        steer /= total
        steer *= strength

    return steer

class Agent:
    def __init__(self):
        self.pos = pygame.Vector2(
            random.randint(0, WIDTH),
            random.randint(0, HEIGHT)
        )
        self.vel = pygame.Vector2(
            random.uniform(-2, 2),
            random.uniform(-2, 2)
        )

    def update(self):
        self.pos += self.vel
        if self.vel.length() > 4:
            self.vel.scale_to_length(4)
        self.edges()

    def edges(self):
        if self.pos.x > WIDTH: self.pos.x = 0
        if self.pos.x < 0: self.pos.x = WIDTH
        if self.pos.y > HEIGHT: self.pos.y = 0
        if self.pos.y < 0: self.pos.y = HEIGHT

    def draw(self, screen):
        pygame.draw.circle(screen, (255, 255, 255),
                           (int(self.pos.x), int(self.pos.y)), 4)
    
    def apply_behaviors(self, agents):
        neighbors = get_neighbors(self, agents, 60)
        align_force = alignment(self, neighbors)
        cohesion_force = cohesion(self, neighbors)
        separation_force = separation(self, neighbors)
        self.vel += align_force
        self.vel += cohesion_force
        self.vel += separation_force