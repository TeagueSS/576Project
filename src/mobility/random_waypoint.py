"""Random-waypoint mobility generator for general roaming behavior."""

import random
import math


class RandomWaypoint:
    def __init__(self, env, node, bounds=(0, 200), speed=(0.5, 2.0)):
        self.env = env
        self.node = node
        self.bounds = bounds
        self.speed_range = speed
        self.target = None

        self.env.process(self.move_process())

    def move_process(self):
        while True:
            # Pick a target
            target_x = random.uniform(*self.bounds)
            target_y = random.uniform(*self.bounds)

            dx = target_x - self.node.x
            dy = target_y - self.node.y
            dist = math.hypot(dx, dy)

            speed = random.uniform(*self.speed_range)
            duration = dist / speed

            steps = int(duration)
            if steps < 1:
                steps = 1

            step_x = dx / steps
            step_y = dy / steps

            for _ in range(steps):
                self.node.x += step_x
                self.node.y += step_y
                yield self.env.timeout(1.0)  # Update every second

            yield self.env.timeout(random.uniform(1, 5))  # Pause at waypoint
