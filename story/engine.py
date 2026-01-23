import random
import pygame
from pygame.math import Vector2

# ---------------- CONFIG ----------------
WIDTH, HEIGHT = 900, 600
NUM_AGENTS = 60

NEIGHBOR_RADIUS = 60
MAX_SPEED = 3

ALIGNMENT_STRENGTH = 0.05
COHESION_STRENGTH = 0.01
SEPARATION_STRENGTH = 0.08
# ----------------------------------------


def limit_speed(v, max_speed):
    if v.length() > max_speed:
        v.scale_to_length(max_speed)
    return v


def get_neighbors(agent, agents, radius):
    neighbors = []
    for other in agents:
        if other != agent:
            if agent.pos.distance_to(other.pos) < radius:
                neighbors.append(other)
    return neighbors


def alignment(agent, neighbors):
    if not neighbors:
        return Vector2()
    avg_vel = sum((n.vel for n in neighbors), Vector2()) / len(neighbors)
    return avg_vel - agent.vel


def cohesion(agent, neighbors):
    if not neighbors:
        return Vector2()
    center = sum((n.pos for n in neighbors), Vector2()) / len(neighbors)
    return center - agent.pos


def separation(agent, neighbors):
    force = Vector2()
    for n in neighbors:
        diff = agent.pos - n.pos
        dist = diff.length()
        if dist > 0:
            force += diff / dist
    return force


class Agent:
    def __init__(self):
        self.pos = Vector2(
            random.uniform(0, WIDTH),
            random.uniform(0, HEIGHT)
        )
        angle = random.uniform(0, 360)
        self.vel = Vector2(1, 0).rotate(angle)

    def apply_behaviors(self, agents):
        neighbors = get_neighbors(self, agents, NEIGHBOR_RADIUS)

        align = alignment(self, neighbors) * ALIGNMENT_STRENGTH
        coh = cohesion(self, neighbors) * COHESION_STRENGTH
        sep = separation(self, neighbors) * SEPARATION_STRENGTH

        self.vel += align + coh + sep
        self.vel = limit_speed(self.vel, MAX_SPEED)

    def update(self):
        self.pos += self.vel

    def edges(self):
        if self.pos.x < 0:
            self.pos.x = WIDTH
        elif self.pos.x > WIDTH:
            self.pos.x = 0

        if self.pos.y < 0:
            self.pos.y = HEIGHT
        elif self.pos.y > HEIGHT:
            self.pos.y = 0

