from collections import defaultdict
import random

# ---------------------------
# Agent Names
# ---------------------------
AGENT_NAMES_LIST = [
    "Astra","Blip","Cleo","Dax","Echo","Fizz","Glim","Haze",
    "Iris","Juno","Kip","Luna","Milo","Nova","Orin","Pip",
    "Quinn","Rex","Sage","Tess","Uma","Vex","Wren","Xan",
    "Yara","Zed","Faye","Nico","Rina","Taro","Zara","Leo",
    "Mara","Koda","Vira","Eli","Ryo","Lina","Sora","Kai",
    "Jace","Naya","Rex","Fia","Zeno","Aya","Tia","Rem","Lio","Zia",
]

NUM_AGENTS = 60  
AGENT_NAMES = {i: AGENT_NAMES_LIST[i % len(AGENT_NAMES_LIST)] for i in range(NUM_AGENTS)}

# ---------------------------
# Story Mapper
# ---------------------------
class StoryMapper:
    def __init__(self):
        self.story_events = []
        self.relationships = defaultdict(int)
        self.proximity_tracker = defaultdict(int)
        self.last_seen_frame = {}
        self.formed_alliances = set()
        self.ALLIANCE_THRESHOLD = 20  # frames for alliance formation

    # Determine story phase
    def _get_phase(self, frame, total_frames):
        if frame < total_frames * 0.3:
            return "introduction"
        elif frame < total_frames * 0.7:
            return "rising_conflict"
        else:
            return "climax"

    # Process events
    def process_event(self, event, total_frames):
        frame = event.get("frame")
        etype = event.get("type")
        agents = event.get("info", {}).get("agents", [])

        phase = self._get_phase(frame, total_frames)

        # ---- Collisions: Tension → Conflict → Rivalry ----
        if etype == "collision" and len(agents) == 2:
            pair = tuple(sorted(agents))
            self.relationships[pair] += 1
            count = self.relationships[pair]

            if count == 1:
                story_type = "tension"
            elif count < 4:
                story_type = "conflict"
            else:
                story_type = "rivalry"

            self.story_events.append({
                "frame": frame,
                "event_type": "collision",
                "agents": pair,
                "story_type": story_type,
                "phase": phase,
                "intensity": count
            })

        # ---- Proximity: Alliance ----
        if etype == "proximity" and len(agents) >= 3:
            group = tuple(sorted(agents))
            last_frame = self.last_seen_frame.get(group, -1)

            if frame != last_frame + 1:
                self.proximity_tracker[group] = 1
            else:
                self.proximity_tracker[group] += 1

            self.last_seen_frame[group] = frame

            if self.proximity_tracker[group] >= self.ALLIANCE_THRESHOLD and group not in self.formed_alliances:
                self.formed_alliances.add(group)
                self.story_events.append({
                    "frame": frame,
                    "event_type": "group_merge",
                    "agents": group,
                    "story_type": "alliance",
                    "phase": phase,
                    "intensity": self.proximity_tracker[group]
                })

    # JSON output
    def generate_story_json(self):
        return {"story_events": self.story_events}

    # Textual narrative
    def generate_story_text(self):
        if not self.story_events:
            return ["The swarm moved in silence, with no notable interactions."]

        story = ["📖 Swarm Narrative\n"]
        current_phase = None
        seen_pairs = set()  # track (pair/group, story_type) globally

        # Optional narrative phrases for variation
        conflict_phrases = [
            "erupted into repeated confrontations",
            "clashed multiple times",
            "had escalating tensions",
            "engaged in a fierce standoff",
        ]
        rivalry_phrases = [
            "escalated into a lasting rivalry",
            "became a defining force within the swarm",
            "remained in conflict throughout the simulation",
        ]
        alliance_phrases = [
            "formed a strategic alliance",
            "stayed close long enough to coordinate",
            "banded together for mutual benefit",
        ]

        for e in self.story_events:
            phase = e["phase"]
            agents = e["agents"]
            stype = e["story_type"]

            # Phase header
            if phase != current_phase:
                if phase == "introduction":
                    story.append("\n🌱 INTRODUCTION\n")
                    story.append("At the beginning of the simulation, the swarm drifted calmly, its agents unaware of the tensions that would soon emerge.")
                elif phase == "rising_conflict":
                    story.append("\n⚡ RISING CONFLICT\n")
                    story.append("As time passed, repeated encounters shaped relationships, and subtle tensions grew into open confrontations.")
                elif phase == "climax":
                    story.append("\n🔥 CLIMAX\n")
                    story.append("In the final moments, unresolved conflicts surfaced, defining the fate of the swarm.")
                current_phase = phase

            # Skip duplicates
            key = (tuple(agents), stype)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)

            # Map agent numbers to names
            names = [AGENT_NAMES[a] for a in agents]

            # Generate narrative line
            if stype == "tension":
                line = f"Agents {names[0]} and {names[1]} crossed paths, sensing unease for the first time."
            elif stype == "conflict":
                phrase = random.choice(conflict_phrases)
                line = f"Agents {names[0]} and {names[1]} {phrase}."
            elif stype == "rivalry":
                phrase = random.choice(rivalry_phrases)
                line = f"Agents {names[0]} and {names[1]} {phrase}."
            elif stype == "alliance":
                phrase = random.choice(alliance_phrases)
                line = f"Agents {', '.join(names)} {phrase}."
            else:
                line = f"Agents {', '.join(names)} interacted."

            story.append(line)

        # Epilogue
        story.append(
            "\n🧠 Epilogue:\n"
            "Though governed by simple rules, the swarm revealed complex relationships—a reminder that stories can emerge even from mathematics."
        )

        return story







