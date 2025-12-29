import pygame
import random
from noise import pnoise2
import math

FLOW_SCALE = 0.004
FLOW_STRENGTH = 0.25

WIDTH = 800
HEIGHT = 600
ART_MODE = "composition"
EMOTION = "calm"
ROTATION_SYMMETRY = 6
CENTER_X = WIDTH / 2
CENTER_Y = HEIGHT / 2

FOCAL_POINTS = [
    (WIDTH * 0.25, HEIGHT * 0.35),
    (WIDTH * 0.75, HEIGHT * 0.30),
    (WIDTH * 0.35, HEIGHT * 0.75),
    (WIDTH * 0.70, HEIGHT * 0.70),
]

def update_focal_points(t):
    new_points = []
    speed = 0.3
    radius = 50
    for (x, y) in FOCAL_POINTS:
        nx = x + math.sin(t * speed + x) * radius
        ny = y + math.cos(t * speed + y) * radius
        new_points.append((nx, ny))
    return new_points

NEGATIVE_ZONES = [
    (WIDTH * 0.5, HEIGHT * 0.5, 250),
]

EMOTION_SETTINGS = {
    "calm": {
        "align": 0.03,
        "cohesion": 0.003,
        "separation": 0.1,
        "focal": 0.01,
        "neg": 0.05
    },
    "anxiety": {
        "align": 0.08,
        "cohesion": 0.0005,
        "separation": 0.3,
        "focal": 0.03,
        "neg": 0.12
    },
    "joy": {
        "align": 0.06,
        "cohesion": 0.01,
        "separation": 0.15,
        "focal": 0.02,
        "neg": 0.02
    }
}

def get_flow_vector(x, y, t):
    angle = pnoise2(x * FLOW_SCALE, y * FLOW_SCALE, repeatx=999999, repeaty=999999, base=int(t)) * 8 * 3.14159
    vec = pygame.Vector2(1, 0).rotate_rad(angle)
    return vec

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

def random_color_palette():
    palettes = [
        [(255, 99, 71), (255, 178, 102), (255, 255, 153)],          # warm sunset
        [(102, 178, 255), (0, 102, 204), (0, 51, 102)],             # blue ocean
        [(255, 102, 178), (255, 153, 204), (204, 0, 102)],          # pink neon
        [(102, 255, 178), (0, 153, 102), (0, 204, 153)],            # mint lush
        [(255, 255, 255), (200, 200, 255), (150, 150, 255)]         # soft galaxy
    ]
    import random
    return random.choice(palettes)

def focal_force(agent, strength=0.01, t=0):
    points = update_focal_points(t)
    force = pygame.Vector2(0, 0)
    for (fx, fy) in points:
        point = pygame.Vector2(fx, fy)
        diff = point - agent.pos
        force += diff
    force /= len(points)
    force *= strength
    return force

def negative_space_force(agent, strength=0.08):
    force = pygame.Vector2(0, 0)

    for (nx, ny, r) in NEGATIVE_ZONES:
        center = pygame.Vector2(nx, ny)
        dist = agent.pos.distance_to(center)

        if dist < r:
            diff = agent.pos - center
            if dist != 0:
                diff /= dist
            force += diff

    force *= strength
    return force

def rotate_point(x, y, cx, cy, angle):
    rad = math.radians(angle)
    dx = x - cx
    dy = y - cy

    rx = dx * math.cos(rad) - dy * math.sin(rad)
    ry = dx * math.sin(rad) + dy * math.cos(rad)

    return cx + rx, cy + ry

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
        self.color = random.choice(random_color_palette())
        self.history = []

    def update(self):
        self.pos += self.vel
        if self.vel.length() > 4:
            self.vel.scale_to_length(4)
        self.edges()
        self.history.append(self.pos.copy())
        if len(self.history) > 20:
            self.history.pop(0)

    def edges(self):
        if self.pos.x > WIDTH: self.pos.x = 0
        if self.pos.x < 0: self.pos.x = WIDTH
        if self.pos.y > HEIGHT: self.pos.y = 0
        if self.pos.y < 0: self.pos.y = HEIGHT

    def draw(self, screen):
        for p in self.history:
            pygame.draw.circle(screen, self.color, (int(p.x), int(p.y)), 2)
        pygame.draw.circle(screen, self.color, (int(self.pos.x), int(self.pos.y)), 3)
        angle_step = 360 / ROTATION_SYMMETRY
        for i in range(1, ROTATION_SYMMETRY):
            angle = angle_step * i
            rx, ry = rotate_point(self.pos.x, self.pos.y, CENTER_X, CENTER_Y, angle)
            pygame.draw.circle(screen, self.color, (int(rx), int(ry)), 3)
        hx = WIDTH - self.pos.x
        hy = self.pos.y
        pygame.draw.circle(screen, self.color, (int(hx), int(hy)), 2)
        vx = self.pos.x
        vy = HEIGHT - self.pos.y
        pygame.draw.circle(screen, self.color, (int(vx), int(vy)), 2)
        dx = WIDTH - self.pos.x
        dy = HEIGHT - self.pos.y
        pygame.draw.circle(screen, self.color, (int(dx), int(dy)), 2)
    
    def apply_behaviors(self, agents, time=None):
        neighbors = get_neighbors(self, agents, 60)
        if ART_MODE == "calm":
            align_force = alignment(self, neighbors, 0.04)
            cohesion_force = cohesion(self, neighbors, 0.003)
            separation_force = separation(self, neighbors, 25, 0.12)

        elif ART_MODE == "chaos":
            align_force = alignment(self, neighbors, 0.1)
            cohesion_force = cohesion(self, neighbors, 0.02)
            separation_force = separation(self, neighbors, 20, 0.25)

        elif ART_MODE == "galaxy":
            align_force = alignment(self, neighbors, 0.03)
            cohesion_force = cohesion(self, neighbors, 0.005)
            separation_force = separation(self, neighbors, 30, 0.1)

        else:
            align_force = cohesion_force = separation_force = pygame.Vector2(0,0)

        if ART_MODE == "flow":
            flow = get_flow_vector(self.pos.x, self.pos.y, time)
            self.vel += flow * FLOW_STRENGTH
        else:
            self.vel += align_force
            self.vel += cohesion_force
            self.vel += separation_force

        if ART_MODE == "composition":
            s = EMOTION_SETTINGS[EMOTION]
            neighbors = get_neighbors(self, agents, 70)
            align_force = alignment(self, neighbors, s["align"])
            cohesion_force = cohesion(self, neighbors, s["cohesion"])
            separation_force = separation(self, neighbors, 28, s["separation"])
            focus = focal_force(self, s["focal"], time)
            neg_space = negative_space_force(self, s["neg"])
            self.vel += align_force
            self.vel += cohesion_force
            self.vel += separation_force
            self.vel += focus
            self.vel += neg_space