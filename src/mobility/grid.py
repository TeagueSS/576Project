"""Grid movement model for slowly roaming clients (e.g., along hallways)."""

import random
import math

class GridMobility:
    def __init__(self, env, node, bounds=(0, 200), speed=(0.5, 1.5), grid_step=20):
        self.env = env
        self.node = node
        self.bounds = bounds
        self.speed_range = speed
        self.grid_step = grid_step  # Distance between "hallways"

        # Snap starting position to nearest grid intersection
        self.node.x = round(self.node.x / grid_step) * grid_step
        self.node.y = round(self.node.y / grid_step) * grid_step

        self.env.process(self.move_process())

    def move_process(self):
        while True:
            # 1. Pick a random intersection on the grid
            max_step = int(self.bounds[1] / self.grid_step)
            target_x = random.randint(0, max_step) * self.grid_step
            target_y = random.randint(0, max_step) * self.grid_step

            # 2. Move along X-axis first (Hallway A)
            if self.node.x != target_x:
                yield self.env.process(self._move_to(target_x, self.node.y))

            # 3. Pause briefly at intersection
            yield self.env.timeout(random.uniform(1.0, 3.0))

            # 4. Move along Y-axis (Hallway B)
            if self.node.y != target_y:
                yield self.env.process(self._move_to(self.node.x, target_y))

            # 5. Wait at destination
            yield self.env.timeout(random.uniform(5.0, 15.0))

    def _move_to(self, dest_x, dest_y):
        dx = dest_x - self.node.x
        dy = dest_y - self.node.y
        dist = math.hypot(dx, dy)

        if dist == 0:
            return

        speed = random.uniform(*self.speed_range)
        duration = dist / speed

        # Animate movement in 1-second chunks
        steps = int(duration)
        if steps < 1: steps = 1

        step_x = dx / steps
        step_y = dy / steps

        for _ in range(steps):
            self.node.x += step_x
            self.node.y += step_y
            yield self.env.timeout(1.0)

        # Ensure final position is exact
        self.node.x = dest_x
        self.node.y = dest_y