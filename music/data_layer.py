# data_layer.py
# ---------------- Data Layer ----------------
# Stores and manages swarm state for creative mapping

import copy

class SwarmStateBuffer:
    """
    Logs positions, velocities, and optional cluster info of agents per frame.
    """
    def __init__(self):
        self.frames = []  # list of frames, each frame = list of agent states

    def log_frame(self, agents):
        """
        Logs the current state of all agents.
        Each agent's state: {'pos': (x, y), 'vel': (vx, vy)}
        """
        frame_data = []
        for agent in agents:
            state = {
                'pos': (agent.pos.x, agent.pos.y),
                'vel': (agent.vel.x, agent.vel.y)
            }
            frame_data.append(state)
        self.frames.append(frame_data)

    def get_frame(self, index):
        """
        Returns the logged state of a specific frame.
        """
        if 0 <= index < len(self.frames):
            return copy.deepcopy(self.frames[index])
        else:
            return None

    def clear(self):
        """Clears all logged frames."""
        self.frames = []

    def total_frames(self):
        return len(self.frames)


class EventLogger:
    """
    Logs events in the swarm, e.g., collisions, group merges, density changes.
    """
    def __init__(self):
        self.events = []  # list of dicts: {'frame': n, 'type': event_type, 'info': {...}}

    def log_event(self, frame_number, event_type, info=None):
        """
        Log an event that happened during the simulation.
        """
        event = {
            'frame': frame_number,
            'type': event_type,
            'info': info or {}
        }
        self.events.append(event)

    def get_events(self):
        return self.events

    def clear(self):
        self.events = []
