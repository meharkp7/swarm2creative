import pygame
import random
import json

WIDTH = 800
HEIGHT = 600
SHOW_STRUCTURE = False
SHOW_CONNECTIVITY = False
SHOW_HIERARCHY = False
SHOW_DOORS = False
STRUCTURAL_EDGES = set()
ARCHITECTURE_MODE = False
ARCH_COMMITTED = False
WALL_HITS = {}
ROOM_HITS = {}
ROOM_AGE = {}
ROOM_TYPES = {}

ARCHITECTURE = {
    "columns": [],
    "primary_columns": [],
    "secondary_columns": [],
    "floors": [],
    "beams": [],
    "core": None,
    "ramps": [],
    "rooms": [],
    "doors": [],
    "walls": [],
    "agents": []
}

ROOM_GRAPH = {
    "adjacencies": {},
    "door_links": {},
    "circulation_rooms": set(),
    "isolated_rooms": set()
}

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

def export_architecture(agents):
    data = {
        "points": [],
        "width": WIDTH,
        "height": HEIGHT
    }
    for agent in agents:
        data["points"].extend(agent.path)
    with open("architecture_paths.json", "w") as f:
        json.dump(data, f, indent=4)
    print("🏛 Exported → architecture_paths.json")

def get_room_key(room):
    """Convert room rect to hashable key"""
    return (room.x, room.y, room.w, room.h)

def point_in_room(point, room, margin=5):
    """Check if point is inside room with margin"""
    return room.inflate(margin, margin).collidepoint(point)

def get_room_at_point(point):
    """Find which room contains a point, if any"""
    for room in ARCHITECTURE["rooms"]:
        if point_in_room(point, room, margin=-5):
            return get_room_key(room)
    return None

def build_room_connectivity_graph():
    """Build complete connectivity graph from rooms and doors"""
    global ROOM_GRAPH
    
    ROOM_GRAPH = {
        "adjacencies": {},
        "door_links": {},
        "circulation_rooms": set(),
        "isolated_rooms": set()
    }
    
    for room in ARCHITECTURE["rooms"]:
        key = get_room_key(room)
        ROOM_GRAPH["adjacencies"][key] = set()
    
    for door_idx, door in enumerate(ARCHITECTURE["doors"]):
        pos = door["pos"]
        normal = door["normal"]
        
        side_a = pos + normal * 15
        side_b = pos - normal * 15
        
        room_a = get_room_at_point(side_a)
        room_b = get_room_at_point(side_b)
        
        if room_a and room_b:
            ROOM_GRAPH["adjacencies"][room_a].add(room_b)
            ROOM_GRAPH["adjacencies"][room_b].add(room_a)
            ROOM_GRAPH["door_links"][door_idx] = (room_a, room_b)
        elif room_a and not room_b:
            ROOM_GRAPH["circulation_rooms"].add(room_a)
            ROOM_GRAPH["door_links"][door_idx] = (room_a, "circulation")
        elif room_b and not room_a:
            ROOM_GRAPH["circulation_rooms"].add(room_b)
            ROOM_GRAPH["door_links"][door_idx] = (room_b, "circulation")
    
    for room in ARCHITECTURE["rooms"]:
        key = get_room_key(room)
        if (len(ROOM_GRAPH["adjacencies"][key]) == 0 and 
            key not in ROOM_GRAPH["circulation_rooms"]):
            ROOM_GRAPH["isolated_rooms"].add(key)

def get_circulation_distance(room_key):
    """Get minimum number of rooms to traverse to reach circulation"""
    if room_key in ROOM_GRAPH["circulation_rooms"]:
        return 0
    
    visited = {room_key}
    queue = [(room_key, 0)]
    
    while queue:
        current, depth = queue.pop(0)
        
        for neighbor in ROOM_GRAPH["adjacencies"].get(current, set()):
            if neighbor in visited:
                continue
            if neighbor in ROOM_GRAPH["circulation_rooms"]:
                return depth + 1
            visited.add(neighbor)
            queue.append((neighbor, depth + 1))
    
    return -1

def draw_connectivity_debug(screen):
    """Visualize the connectivity graph"""
    for room_key, neighbors in ROOM_GRAPH["adjacencies"].items():
        room = next((r for r in ARCHITECTURE["rooms"] if get_room_key(r) == room_key), None)
        if not room:
            continue
        center_a = pygame.Vector2(room.center)
        
        for neighbor_key in neighbors:
            neighbor = next((r for r in ARCHITECTURE["rooms"] if get_room_key(r) == neighbor_key), None)
            if not neighbor:
                continue
            center_b = pygame.Vector2(neighbor.center)
            pygame.draw.line(screen, (100, 255, 100), center_a, center_b, 2)
    
    for room_key in ROOM_GRAPH["circulation_rooms"]:
        room = next((r for r in ARCHITECTURE["rooms"] if get_room_key(r) == room_key), None)
        if room:
            pygame.draw.rect(screen, (100, 255, 255), room, 3)
    
    for room_key in ROOM_GRAPH["isolated_rooms"]:
        room = next((r for r in ARCHITECTURE["rooms"] if get_room_key(r) == room_key), None)
        if room:
            pygame.draw.rect(screen, (255, 100, 100), room, 3)

def validate_and_lock_doors(min_door_spacing=25):
    """Ensure doors are properly validated"""
    valid_doors = []
    used_walls = {}
    
    for door in ARCHITECTURE["doors"]:
        pos = door["pos"]
        wall = door["wall"]
        
        wall_id = (wall[0].x, wall[0].y, wall[1].x, wall[1].y)
        
        if wall_id in used_walls:
            too_close = False
            for existing_pos in used_walls[wall_id]:
                if pos.distance_to(existing_pos) < min_door_spacing:
                    too_close = True
                    break
            if too_close:
                continue
        
        valid_doors.append(door)
        
        if wall_id not in used_walls:
            used_walls[wall_id] = []
        used_walls[wall_id].append(pos)
    
    ARCHITECTURE["doors"] = valid_doors
    ensure_minimum_exits()

def ensure_minimum_exits(min_exits=1):
    """Ensure every room has at least one exit door"""
    room_door_count = {}
    
    for door in ARCHITECTURE["doors"]:
        room_key = door["room"]
        room_door_count[room_key] = room_door_count.get(room_key, 0) + 1
    
    for room in ARCHITECTURE["rooms"]:
        key = get_room_key(room)
        if room_door_count.get(key, 0) < min_exits:
            create_emergency_door(room, key)

def create_emergency_door(room, room_key):
    """Create an emergency door for isolated room"""
    walls = [
        (pygame.Vector2(room.left, room.top), pygame.Vector2(room.right, room.top)),
        (pygame.Vector2(room.left, room.bottom), pygame.Vector2(room.right, room.bottom)),
        (pygame.Vector2(room.left, room.top), pygame.Vector2(room.left, room.bottom)),
        (pygame.Vector2(room.right, room.top), pygame.Vector2(room.right, room.bottom))
    ]
    
    center = pygame.Vector2(WIDTH / 2, HEIGHT / 2)
    best_wall = min(walls, key=lambda w: ((w[0] + w[1]) / 2).distance_to(center))
    
    a, b = best_wall
    pos = (a + b) / 2
    normal = (b - a).normalize().rotate(90)
    
    ARCHITECTURE["doors"].append({
        "pos": pos,
        "room": room_key,
        "wall": (a, b),
        "normal": normal,
        "emergency": True
    })

def build_circulation_hierarchy():
    """Create hierarchical circulation structure"""
    hierarchy = {
        "spine": set(),
        "primary_branch": set(),
        "secondary_branch": set(),
        "terminal": set()
    }
    
    for room_key in ROOM_GRAPH["circulation_rooms"]:
        room = next((r for r in ARCHITECTURE["rooms"] if get_room_key(r) == room_key), None)
        if room:
            on_primary = any(abs(room.centery - y) < 30 for y in ARCHITECTURE.get("primary_floors", []))
            if on_primary:
                hierarchy["spine"].add(room_key)
    
    for room in ARCHITECTURE["rooms"]:
        key = get_room_key(room)
        dist = get_circulation_distance(key)
        
        if key in hierarchy["spine"]:
            continue
        elif dist == 0:
            hierarchy["primary_branch"].add(key)
        elif dist == 1:
            hierarchy["secondary_branch"].add(key)
        else:
            hierarchy["terminal"].add(key)
    
    ARCHITECTURE["circulation_hierarchy"] = hierarchy
    
    print(f"🏗️  Hierarchy: {len(hierarchy['spine'])} spine, {len(hierarchy['primary_branch'])} primary, {len(hierarchy['secondary_branch'])} secondary, {len(hierarchy['terminal'])} terminal")
    
    return hierarchy

def apply_hierarchy_room_types():
    """Auto-assign room types based on circulation hierarchy"""
    if "circulation_hierarchy" not in ARCHITECTURE:
        build_circulation_hierarchy()
    
    hierarchy = ARCHITECTURE["circulation_hierarchy"]
    
    for room in ARCHITECTURE["rooms"]:
        key = get_room_key(room)
        
        if key in hierarchy["spine"] or key in hierarchy["primary_branch"]:
            ROOM_TYPES[key] = "public"
        elif key in hierarchy["secondary_branch"]:
            if ROOM_TYPES.get(key) not in ["public", "private"]:
                ROOM_TYPES[key] = "service"
        elif key in hierarchy["terminal"]:
            ROOM_TYPES[key] = "private"

def circulation_hierarchy_force(agent):
    """Agent behavior based on circulation hierarchy"""
    if "circulation_hierarchy" not in ARCHITECTURE:
        return pygame.Vector2(0, 0)
    
    force = pygame.Vector2(0, 0)
    hierarchy = ARCHITECTURE["circulation_hierarchy"]
    
    for room in ARCHITECTURE["rooms"]:
        key = get_room_key(room)
        if not room.collidepoint(agent.pos):
            continue
        
        if key in hierarchy["spine"]:
            if abs(agent.vel.x) > 0.1:
                force.x += 0.3 * (1 if agent.vel.x > 0 else -1)
        
        elif key in hierarchy["terminal"]:
            for circ_key in ROOM_GRAPH["circulation_rooms"]:
                circ_room = next((r for r in ARCHITECTURE["rooms"] if get_room_key(r) == circ_key), None)
                if circ_room:
                    dir = pygame.Vector2(circ_room.center) - agent.pos
                    if dir.length() > 0:
                        force += dir.normalize() * 0.12
                    break
    
    return force

def smart_prune_rooms(min_hits=40, min_age=240):
    """Intelligent pruning that considers connectivity"""
    alive = []
    
    for r in ARCHITECTURE["rooms"]:
        key = get_room_key(r)
        hits = ROOM_HITS.get(key, 0)
        age = ROOM_AGE.get(key, 0)
        
        if age < min_age:
            alive.append(r)
            continue
        
        is_isolated = key in ROOM_GRAPH["isolated_rooms"]
        has_circulation = key in ROOM_GRAPH["circulation_rooms"]
        neighbor_count = len(ROOM_GRAPH["adjacencies"].get(key, set()))
        
        if is_isolated and hits < min_hits * 1.5:
            continue
        
        if has_circulation and hits >= min_hits * 0.5:
            alive.append(r)
            continue
        
        if neighbor_count >= 2 and hits >= min_hits * 0.7:
            alive.append(r)
            continue
        
        if hits >= min_hits:
            alive.append(r)
    
    ARCHITECTURE["rooms"] = alive
    build_room_connectivity_graph()
    
    print(f"🧹 Smart prune → {len(alive)} rooms, {len(ROOM_GRAPH['isolated_rooms'])} isolated")

def needs_visual_refresh():
    """Check if architecture visuals need updating"""
    if not hasattr(needs_visual_refresh, "last_door_count"):
        needs_visual_refresh.last_door_count = 0
    
    current_doors = len(ARCHITECTURE["doors"])
    if current_doors != needs_visual_refresh.last_door_count:
        needs_visual_refresh.last_door_count = current_doors
        return True
    
    return False

def refresh_architecture_surface(surface):
    """Redraw architecture on surface"""
    surface.fill((0, 0, 0, 0))
    draw_architecture(surface)

def draw_circulation_hierarchy(screen):
    """Visualize the circulation hierarchy"""
    if "circulation_hierarchy" not in ARCHITECTURE:
        return
    
    hierarchy = ARCHITECTURE["circulation_hierarchy"]
    
    for key in hierarchy["spine"]:
        room = next((r for r in ARCHITECTURE["rooms"] if get_room_key(r) == key), None)
        if room:
            pygame.draw.rect(screen, (0, 255, 255), room, 4)
    
    for key in hierarchy["primary_branch"]:
        room = next((r for r in ARCHITECTURE["rooms"] if get_room_key(r) == key), None)
        if room:
            pygame.draw.rect(screen, (255, 255, 0), room, 3)
    
    for key in hierarchy["secondary_branch"]:
        room = next((r for r in ARCHITECTURE["rooms"] if get_room_key(r) == key), None)
        if room:
            pygame.draw.rect(screen, (255, 165, 0), room, 2)
    
    for key in hierarchy["terminal"]:
        room = next((r for r in ARCHITECTURE["rooms"] if get_room_key(r) == key), None)
        if room:
            pygame.draw.rect(screen, (180, 50, 50), room, 2)

def draw_door_info(screen):
    """Show door information"""
    font = pygame.font.Font(None, 16)
    
    for idx, door in enumerate(ARCHITECTURE["doors"]):
        pos = door["pos"]
        is_emergency = door.get("emergency", False)
        color = (255, 100, 100) if is_emergency else (100, 255, 100)
        
        if idx in ROOM_GRAPH["door_links"]:
            link = ROOM_GRAPH["door_links"][idx]
            if link[1] == "circulation":
                text = font.render("→C", True, (100, 255, 255))
            else:
                text = font.render("↔", True, color)
            screen.blit(text, (int(pos.x) - 8, int(pos.y) - 20))

def draw_architecture(screen):
    xs = [c.x for c in ARCHITECTURE["columns"]]
    if len(xs) >= 2:
        left = min(xs)
        right = max(xs)
        for y in ARCHITECTURE["floors"]:
            draw_wall_with_doors(screen, y, left, right)

    COLUMN_HALF_HEIGHT = 180
    for c in ARCHITECTURE["primary_columns"]:
        ARCHITECTURE["walls"].append((
            pygame.Vector2(c.x, c.y - COLUMN_HALF_HEIGHT),
            pygame.Vector2(c.x, c.y + COLUMN_HALF_HEIGHT)
        ))

    for c in ARCHITECTURE["secondary_columns"]:
        pygame.draw.rect(screen, (170,170,190), 
            pygame.Rect(int(c.x-4), int(c.y-140), 8, 280))
    
    cols = ARCHITECTURE["primary_columns"]
    for i in range(len(cols)-1):
        c1 = cols[i]
        c2 = cols[i+1]
        for y in ARCHITECTURE["floors"]:
            pygame.draw.line(screen, (190,190,210),
                (int(c1.x), int(y)), (int(c2.x), int(y)), 3)
    
    core = ARCHITECTURE.get("core")
    if core:
        pygame.draw.rect(screen, (160,160,180),
            pygame.Rect(int(core.x - 18), int(HEIGHT * 0.2), 36, int(HEIGHT * 0.6)))

    for p1, p2 in ARCHITECTURE["beams"]:
        pygame.draw.line(screen, (200,200,220),
            (int(p1.x), int(p1.y)), (int(p2.x), int(p2.y)), 3)
    
    for p1, p2 in ARCHITECTURE.get("ramps", []):
        pygame.draw.line(screen, (160, 160, 180),
            (int(p1.x), int(p1.y)), (int(p2.x), int(p2.y)), 4)
    
    for room in ARCHITECTURE.get("rooms", []):
        key = (room.x, room.y, room.w, room.h)
        rtype = ROOM_TYPES.get(key, "public")

        if rtype == "public":
            color = (90, 110, 180)
        elif rtype == "private":
            color = (140, 90, 120)
        else:
            color = (90, 140, 120)

        pygame.draw.rect(screen, color, room, 2)

    for d in ARCHITECTURE["doors"]:
        pos = d["pos"]
        n = d["normal"]

        if abs(n.x) > abs(n.y):
            pygame.draw.line(screen, (0,0,0),
                (int(pos.x), int(pos.y - 10)),
                (int(pos.x), int(pos.y + 10)), 6)
        else:
            pygame.draw.line(screen, (0,0,0),
                (int(pos.x - 10), int(pos.y)),
                (int(pos.x + 10), int(pos.y)), 6)

def detect_columns(agents, speed_threshold=0.6, min_count=4):
    columns = []
    for a in agents:
        if a.vel.length() < speed_threshold:
            nearby = [b for b in agents
                if a.pos.distance_to(b.pos) < 25 and b.vel.length() < speed_threshold]
            if len(nearby) >= min_count:
                columns.append(a.pos)
    return columns

def anchor_repulsion(agent, agents, radius=80, strength=0.6):
    force = pygame.Vector2(0,0)
    for other in agents:
        if other is agent:
            continue
        if other.is_anchor:
            d = agent.pos.distance_to(other.pos)
            if d < radius and d > 0:
                diff = agent.pos - other.pos
                diff.normalize_ip()
                force += diff * (strength / d)
    return force

def too_close_to_anchor(agent, agents, min_dist=120):
    for other in agents:
        if other.is_anchor and agent.pos.distance_to(other.pos) < min_dist:
            return True
    return False

def cluster_columns(columns, radius=60):
    clusters = []
    for c in columns:
        placed = False
        for cl in clusters:
            if c.distance_to(cl[0]) < radius:
                cl.append(c)
                placed = True
                break
        if not placed:
            clusters.append([c])
    return clusters

def commit_architecture(agents):
    global ARCH_COMMITTED
    if ARCH_COMMITTED:
        return
    ARCH_COMMITTED = True
    
    ARCHITECTURE["columns"].clear()
    ARCHITECTURE["primary_columns"].clear()
    ARCHITECTURE["secondary_columns"].clear()
    ARCHITECTURE["floors"].clear()
    ARCHITECTURE["beams"].clear()
    ARCHITECTURE["core"] = None
    ARCHITECTURE["ramps"] = []
    ARCHITECTURE["rooms"] = []
    ARCHITECTURE["doors"] = []
    ARCHITECTURE["walls"] = []

    for a in agents:
        if a.is_anchor:
            raw_columns = [pygame.Vector2(a.pos.x, a.pos.y) for a in agents if a.is_anchor]
            column_clusters = cluster_columns(raw_columns)
            ARCHITECTURE["columns"] = [
                sum(cluster, pygame.Vector2(0,0)) / len(cluster)
                for cluster in column_clusters
            ]

    for c in ARCHITECTURE["columns"]:
        if c.y > HEIGHT * 0.4:
            ARCHITECTURE["primary_columns"].append(c)
        else:
            ARCHITECTURE["secondary_columns"].append(c)
    
    ys = [a.pos.y for a in agents]
    ys.sort()
    
    if ARCHITECTURE["primary_columns"]:
        cx = WIDTH / 2
        core = min(ARCHITECTURE["primary_columns"], key=lambda c: abs(c.x - cx))
        ARCHITECTURE["core"] = core

    levels = []
    for y in ys:
        if not any(abs(y - l) < 25 for l in levels):
            levels.append(y)
    for y in levels[:4]:
        ARCHITECTURE["floors"].append(y)
    
    cols = sorted(ARCHITECTURE["columns"], key=lambda c: c.x)
    for i in range(len(cols) - 1):
        if abs(cols[i].y - cols[i+1].y) < 40:
            ARCHITECTURE["beams"].append((cols[i], cols[i+1]))

    floors = ARCHITECTURE["floors"]
    for i in range(len(floors) - 1):
        y1 = floors[i]
        y2 = floors[i + 1]
        if ARCHITECTURE["primary_columns"]:
            col = min(ARCHITECTURE["primary_columns"], key=lambda c: abs(c.x - WIDTH / 2))
            ARCHITECTURE["ramps"].append((
                pygame.Vector2(col.x - 40, y1),
                pygame.Vector2(col.x + 40, y2)
            ))
    
    ARCHITECTURE["primary_floors"] = []
    ARCHITECTURE["secondary_floors"] = []
    center_y = HEIGHT / 2
    for y in ARCHITECTURE["floors"]:
        if abs(y - center_y) < HEIGHT * 0.18:
            ARCHITECTURE["primary_floors"].append(y)
        else:
            ARCHITECTURE["secondary_floors"].append(y)
    
    cols = sorted(ARCHITECTURE["columns"], key=lambda c: c.x)
    floors = sorted(ARCHITECTURE["floors"])
    for i in range(len(cols) - 1):
        for j in range(len(floors) - 1):
            c1 = cols[i]
            c2 = cols[i + 1]
            y1 = floors[j]
            y2 = floors[j + 1]
            width = abs(c2.x - c1.x)
            height = abs(y2 - y1)
            if 60 < width < 220 and 50 < height < 180:
                room = pygame.Rect(
                    int(c1.x + 10), int(y1 + 10),
                    int(width - 20), int(height - 20)
                )
                ARCHITECTURE["rooms"].append(room)
                key = (room.x, room.y, room.w, room.h)
                ROOM_TYPES[key] = random.choice(["public", "private", "service"])

    generate_doors_from_hits()
    validate_and_lock_doors()
    
    ARCHITECTURE["walls"] = []

    for y in ARCHITECTURE["floors"]:
        ARCHITECTURE["walls"].append((
            pygame.Vector2(0, y),
            pygame.Vector2(WIDTH, y)
        ))

    for c in ARCHITECTURE["primary_columns"]:
        ARCHITECTURE["walls"].append((
            pygame.Vector2(c.x, 0),
            pygame.Vector2(c.x, HEIGHT)
        ))

    for r in ARCHITECTURE["rooms"]:
        x, y, w, h = r
        walls = [
            (pygame.Vector2(x, y), pygame.Vector2(x + w, y)),
            (pygame.Vector2(x, y + h), pygame.Vector2(x + w, y + h)),
            (pygame.Vector2(x, y), pygame.Vector2(x, y + h)),
            (pygame.Vector2(x + w, y), pygame.Vector2(x + w, y + h))
        ]

        for a, b in walls:
            n = (b - a).normalize().rotate(90)
            ARCHITECTURE["walls"].extend([
                (a + n*5, b + n*5),
                (a - n*5, b - n*5)
            ])
    
    for p1, p2 in ARCHITECTURE["ramps"]:
        d = p2 - p1
        if d.length_squared() == 0:
            continue
        n = d.normalize().rotate(90)
        ARCHITECTURE["walls"].extend([
            (p1 + n*6, p2 + n*6),
            (p1 - n*6, p2 - n*6)
        ])
    
    build_room_connectivity_graph()
    build_circulation_hierarchy()
    apply_hierarchy_room_types()
    
    print(f"🔗 Connectivity: {len(ROOM_GRAPH['circulation_rooms'])} circulation, {len(ROOM_GRAPH['isolated_rooms'])} isolated")

def circulation_force(agent):
    force = pygame.Vector2(0, 0)

    for y in ARCHITECTURE["floors"]:
        dy = abs(agent.pos.y - y)
        if dy < 20:
            force.x += 0.4 if agent.pos.x < WIDTH/2 else -0.4

    for c in ARCHITECTURE["primary_columns"]:
        dx = abs(agent.pos.x - c.x)
        if dx < 15:
            force.y += 0.5 if agent.pos.y > HEIGHT/2 else -0.5

    core = ARCHITECTURE.get("core")
    if core:
        dir = core - agent.pos
        if dir.length() > 0:
            dir.normalize_ip()
            force += dir * 0.15

    return force

def corridor_force(agent):
    force = pygame.Vector2(0, 0)
    for y in ARCHITECTURE.get("primary_floors", []):
        if abs(agent.pos.y - y) < 10:
            direction = 1 if agent.vel.x >= 0 else -1
            force.x += 1.2 * direction
    for y in ARCHITECTURE.get("secondary_floors", []):
        if abs(agent.pos.y - y) < 10:
            direction = 1 if agent.vel.x >= 0 else -1
            force.x += 0.35 * direction
    return force

def generate_doors_from_hits(
    max_doors_per_room=2,
    threshold=12,
    corner_clearance=18,
    column_clearance=22
):
    doors = []
    for room in ARCHITECTURE["rooms"]:
        key = (room.x, room.y, room.w, room.h)
        hits = WALL_HITS.get(key, [])
        if len(hits) < threshold:
            continue
        walls = [
            (pygame.Vector2(room.left, room.top), pygame.Vector2(room.right, room.top)),
            (pygame.Vector2(room.left, room.bottom), pygame.Vector2(room.right, room.bottom)),
            (pygame.Vector2(room.left, room.top), pygame.Vector2(room.left, room.bottom)),
            (pygame.Vector2(room.right, room.top), pygame.Vector2(room.right, room.bottom))
        ]
        wall_scores = []
        for a, b in walls:
            score = 0
            for h in hits:
                _, d = point_to_segment_distance(h, a, b)
                if d < 12:
                    score += 1
            wall_scores.append((score, a, b))
        wall_scores.sort(reverse=True, key=lambda x: x[0])
        used = 0
        for score, a, b in wall_scores:
            if score < threshold or used >= max_doors_per_room:
                continue
            avg = sum(hits, pygame.Vector2(0, 0)) / len(hits)
            ab = b - a
            t = max(0.1, min(0.9, (avg - a).dot(ab) / ab.length_squared()))
            pos = a + ab * t
            if pos.distance_to(a) < corner_clearance or pos.distance_to(b) < corner_clearance:
                continue
            if any(pos.distance_to(c) < column_clearance for c in ARCHITECTURE["primary_columns"]):
                continue
            normal = (b - a).normalize().rotate(90)
            doors.append({
                "pos": pos,
                "room": key,
                "wall": (a, b),
                "normal": normal
            })
            used += 1
    ARCHITECTURE["doors"] = doors

def record_wall_crossing(agent):
    for room in ARCHITECTURE["rooms"]:
        if room.inflate(6, 6).collidepoint(agent.pos):
            continue
        expanded = room.inflate(14, 14)
        if expanded.collidepoint(agent.pos):
            key = (room.x, room.y, room.w, room.h)
            WALL_HITS.setdefault(key, [])
            WALL_HITS[key].append(agent.pos.copy())

def draw_wall_with_doors(screen, y, x1, x2, thickness=4):
    doors = [d["pos"] for d in ARCHITECTURE["doors"] if abs(d["pos"].y - y) < 8]
    doors.sort(key=lambda d: d.x)
    segments = []
    start = x1
    for d in doors:
        if x1 < d.x < x2:
            segments.append((start, d.x - 14))
            start = d.x + 14
    segments.append((start, x2))
    for a, b in segments:
        if b > a:
            pygame.draw.line(screen, (180,180,200), (int(a), int(y)), (int(b), int(y)), thickness)

def wall_repulsion(agent, buffer=16, strength=1.6):
    force = pygame.Vector2(0, 0)
    for a, b in ARCHITECTURE["walls"]:
        diff, dist = point_to_segment_distance(agent.pos, a, b)
        if dist == 0 or dist > buffer:
            continue
        near_door = False
        for d in ARCHITECTURE["doors"]:
            if agent.pos.distance_to(d["pos"]) < 22:
                near_door = True
                break
        if near_door:
            continue
        if diff.length_squared() > 0:
            diff.normalize_ip()
        else:
            continue
        force += diff * (strength * (buffer - dist) / buffer)
    return force

def wall_velocity_correction(agent):
    for a, b in ARCHITECTURE["walls"]:
        diff, dist = point_to_segment_distance(agent.pos, a, b)
        if dist < 6 and agent.vel.length() > 0:
            if diff.length_squared() == 0:
                continue
            normal = diff.normalize()
            vn = agent.vel.dot(normal)
            if vn < 0:
                agent.vel -= normal * vn

def wall_position_correction(agent, push=6):
    for a, b in ARCHITECTURE["walls"]:
        diff, dist = point_to_segment_distance(agent.pos, a, b)
        if 0 < dist < push and diff.length_squared() > 1e-6:
            agent.pos += diff.normalize() * (push - dist)

def point_to_segment_distance(p, a, b):
    ab = b - a
    t = max(0, min(1, (p - a).dot(ab) / ab.length_squared()))
    closest = a + ab * t
    return (p - closest), (p - closest).length()

def wall_slide_force(agent, strength=0.35):
    force = pygame.Vector2(0,0)
    for a, b in ARCHITECTURE["walls"]:
        diff, dist = point_to_segment_distance(agent.pos, a, b)
        if 4 < dist < 18 and diff.length_squared() > 0:
            normal = diff.normalize()
            tangent = pygame.Vector2(-normal.y, normal.x)
            force += tangent * strength
    return force

def wall_future_block(agent, lookahead=6):
    future = agent.pos + agent.vel
    for a, b in ARCHITECTURE["walls"]:
        _, dist_now = point_to_segment_distance(agent.pos, a, b)
        _, dist_future = point_to_segment_distance(future, a, b)
        if dist_now > 6 and dist_future < 4:
            return True
    return False

def junction_damping(agent, radius=18, damping=0.45):
    count = 0
    for a, b in ARCHITECTURE["walls"]:
        _, dist = point_to_segment_distance(agent.pos, a, b)
        if dist < radius:
            count += 1
            if count >= 2:
                agent.vel *= damping
                return

def door_attraction(agent):
    force = pygame.Vector2(0, 0)
    for d in ARCHITECTURE["doors"]:
        pos = d["pos"]
        normal = d["normal"]
        room_type = ROOM_TYPES.get(d["room"], "public")
        v = pos - agent.pos
        if v.length_squared() == 0:
            continue
        approach = v.normalize().dot(-normal)
        if approach < 0.25:
            continue
        if room_type == "public":
            strength = 0.25
        elif room_type == "private":
            strength = 0.06
        else:
            strength = 0.14
        force += v.normalize() * strength * approach
    return force

def door_clearance(agent, push=0.6):
    for d in ARCHITECTURE["doors"]:
        if agent.pos.distance_to(d["pos"]) < 10:
            diff = agent.pos - d["pos"]
            if diff.length_squared() > 0:
                agent.vel += diff.normalize() * push

def door_snap(agent, strength=0.25):
    for d in ARCHITECTURE["doors"]:
        if agent.pos.distance_to(d["pos"]) < 22:
            dir = d["pos"] - agent.pos
            if dir.length() > 0:
                dir.normalize_ip()
                agent.vel += dir * strength

def door_wrong_side_repulsion(agent, strength=0.35):
    force = pygame.Vector2(0, 0)
    for d in ARCHITECTURE["doors"]:
        pos = d["pos"]
        normal = d["normal"]
        v = agent.pos - pos
        if v.length_squared() == 0:
            continue
        if v.normalize().dot(normal) > 0.2:
            force += v.normalize() * strength
    return force

def door_slow_zone(agent, radius=14):
    for d in ARCHITECTURE["doors"]:
        if agent.pos.distance_to(d["pos"]) < radius:
            agent.vel *= 0.75

def column_repulsion(agent, strength=1.4, radius=26):
    force = pygame.Vector2(0,0)
    for c in ARCHITECTURE["primary_columns"]:
        d = agent.pos.distance_to(c)
        if 0 < d < radius:
            force += (agent.pos - c).normalize() * (strength / d)
    return force

def record_room_usage(agent):
    for r in ARCHITECTURE["rooms"]:
        key = (r.x, r.y, r.w, r.h)
        if r.collidepoint(agent.pos):
            ROOM_HITS[key] = ROOM_HITS.get(key, 0) + 1
            ROOM_AGE[key] = ROOM_AGE.get(key, 0) + 1

def room_behavior_force(agent):
    force = pygame.Vector2(0, 0)
    for room in ARCHITECTURE["rooms"]:
        if not room.inflate(-6, -6).collidepoint(agent.pos):
            continue
        key = (room.x, room.y, room.w, room.h)
        rtype = ROOM_TYPES.get(key, "public")
        center = pygame.Vector2(room.center)
        v = center - agent.pos
        if v.length_squared() == 0:
            continue
        if rtype == "public":
            force += v.normalize() * 0.08 
        elif rtype == "private":
            force -= v.normalize() * 0.06
        elif rtype == "service":
            force += agent.vel.normalize() * 0.12
    return force

def private_room_density_limit(agent, max_agents=3):
    for room in ARCHITECTURE["rooms"]:
        key = (room.x, room.y, room.w, room.h)
        if ROOM_TYPES.get(key) != "private":
            continue
        if room.collidepoint(agent.pos):
            count = sum(1 for a in ARCHITECTURE["agents"] if room.collidepoint(a.pos))
            if count > max_agents:
                agent.vel *= 0.6

def evolve_rooms(min_age=300, promote_hits=140, demote_hits=30, kill_hits=8):
    for room in ARCHITECTURE["rooms"][:]:
        key = (room.x, room.y, room.w, room.h)
        age = ROOM_AGE.get(key, 0)
        hits = ROOM_HITS.get(key, 0)
        rtype = ROOM_TYPES.get(key, "public")
        if age < min_age:
            continue
        if hits >= promote_hits:
            ROOM_TYPES[key] = "public"
        elif hits <= demote_hits and rtype == "public":
            ROOM_TYPES[key] = "service"
        elif hits <= kill_hits and rtype != "service":
            ARCHITECTURE["rooms"].remove(room)
            ROOM_TYPES.pop(key, None)
            ROOM_HITS.pop(key, None)
            ROOM_AGE.pop(key, None)

def decay_room_memory(rate=0.995):
    for k in ROOM_HITS:
        ROOM_HITS[k] *= rate

class Agent:
    def __init__(self):
        self.pos = pygame.Vector2(random.randint(0, WIDTH), random.randint(0, HEIGHT))
        self.vel = pygame.Vector2(random.uniform(-2, 2), random.uniform(-2, 2))
        self.path = []
        self.arch_path = []
        self.is_anchor = False
        self.last_room = None

    def update(self, agents):
        self.pos += self.vel
        if self.vel.length() > 4:
            self.vel.scale_to_length(4)
        self.edges()
        self.path.append((self.pos.x, self.pos.y))
        if len(self.path) > 500:
            self.path.pop(0)
        self.arch_path.append(self.pos.copy())
        if len(self.arch_path) > 400:
            self.arch_path.pop(0)
        if not self.is_anchor and self.vel.length() < 0.50 and len(self.path) > 120:
            self.is_anchor = True
            self.vel *= 0
        if (not self.is_anchor and self.vel.length() < 0.50 and 
            len(self.path) > 120 and not too_close_to_anchor(self, agents)):
            self.is_anchor = True
            self.vel *= 0
        if ARCHITECTURE_MODE:
            record_wall_crossing(self)
            record_room_usage(self)
        for room in ARCHITECTURE["rooms"]:
            if room.collidepoint(self.pos):
                self.last_room = room

    def edges(self):
        if self.pos.x > WIDTH: self.pos.x = 0
        if self.pos.x < 0: self.pos.x = WIDTH
        if self.pos.y > HEIGHT: self.pos.y = 0
        if self.pos.y < 0: self.pos.y = HEIGHT

    def draw(self, screen):
        pygame.draw.circle(screen, (255, 255, 255), (int(self.pos.x), int(self.pos.y)), 4)
    
    def apply_behaviors(self, agents):
        if ARCHITECTURE_MODE:
            self.vel *= 0.9
            self.vel += circulation_force(self)
            self.vel += corridor_force(self)
            self.vel += circulation_hierarchy_force(self)
            self.vel += wall_repulsion(self)
            self.vel += wall_slide_force(self)
            self.vel += door_attraction(self) * 0.6
            self.vel += door_wrong_side_repulsion(self)
            self.vel += column_repulsion(self)
            self.vel += room_behavior_force(self)

            door_snap(self)
            junction_damping(self)
            wall_velocity_correction(self)
            wall_position_correction(self)
            door_clearance(self)
            private_room_density_limit(self)

            for room in ARCHITECTURE["rooms"]:
                key = (room.x, room.y, room.w, room.h)
                if room.inflate(-6, -6).collidepoint(self.pos):
                    rtype = ROOM_TYPES.get(key)
                    if rtype == "public":
                        self.vel *= 0.92
                    elif rtype == "private":
                        self.vel *= 0.80
                    elif rtype == "service":
                        self.vel *= 1.05

            if wall_future_block(self):
                self.vel *= 0.2

            if self.vel.length_squared() > 1e-6:
                self.vel = self.vel.clamp_magnitude(2.6)
            else:
                self.vel.update(0, 0)
            return

        neighbors = get_neighbors(self, agents, 60)
        self.vel += alignment(self, neighbors)
        self.vel += cohesion(self, neighbors)
        self.vel += separation(self, neighbors)
        for other in agents:
            if other.is_anchor:
                d = self.pos.distance_to(other.pos)
                if 0 < d < 120:
                    diff = self.pos - other.pos
                    diff.normalize_ip()
                    self.vel += diff * (0.3 / d)
        if self.vel.length_squared() > 0:
            self.vel = self.vel.clamp_magnitude(2.2)