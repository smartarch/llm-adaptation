from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        DRONE_SPEED = 2.0

        def field_center(f):
            return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        def arrival_time(drone, field):
            # Already protecting on-site -> zero arrival time
            if getattr(drone, "state", None) == "protecting" and drone.target_id == field.id:
                return 0.0
            cx, cy = field_center(field)
            dx = getattr(drone.location, "x", 0) - cx
            dy = getattr(drone.location, "y", 0) - cy
            return math.hypot(dx, dy) / DRONE_SPEED

        idle_group = "idle"

        fields = list(getattr(environment, "fields", []) or [])
        threatened = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, set all drones to idle
        if not threatened:
            for c in components:
                environment.assign_group(c, idle_group)
            return

        # Sort fields by descending threat level (tie-breaker by id for determinism)
        threatened.sort(key=lambda f: (f.threat_level, str(f.id)), reverse=True)

        # Prepare assignment map and available drones pool
        assigned = {}  # component -> group name
        available = list(components)  # drones not yet assigned in this step

        # Helper: count and assign contributors (protecting or moving_to_field for that field)
        def assign_contributors_for_field(field):
            contrib = []
            for d in list(available):
                if getattr(d, "target_id", None) == field.id and getattr(d, "state", None) in ("protecting", "moving_to_field"):
                    contrib.append(d)
            for d in contrib:
                assigned[d] = f"protecting {field.id}"
                if d in available:
                    available.remove(d)
            return len(contrib)

        # Iterate fields in priority order
        for idx, field in enumerate(threatened):
            required = int(getattr(field, "drones_for_full_protection", 0))
            if required <= 0:
                continue

            # Assign contributors (protecting or moving_to_field toward this field)
            already = assign_contributors_for_field(field)
            need = max(0, required - already)

            if need == 0:
                # Field already has sufficient contributors; keep them assigned
                continue

            # For the top field: use nearest available drones even if that uses up most drones
            if idx == 0:
                if available:
                    # sort available by arrival time to this field
                    available.sort(key=lambda d: arrival_time(d, field))
                    to_take = available[:need]
                    for d in to_take:
                        assigned[d] = f"protecting {field.id}"
                    # remove taken from available
                    available = [d for d in available if assigned.get(d) != f"protecting {field.id}"]
                # after this, whether fully satisfied or not, move on (we prioritized top field)
                continue

            # For other fields: only assign if we can fully satisfy requirement using currently available drones
            if len(available) >= need:
                # choose nearest 'need' drones by arrival time
                available.sort(key=lambda d: arrival_time(d, field))
                to_take = available[:need]
                for d in to_take:
                    assigned[d] = f"protecting {field.id}"
                # remove taken from available
                available = [d for d in available if assigned.get(d) != f"protecting {field.id}"]
            else:
                # not enough available drones to fully protect this field; skip it
                continue

        # Any remaining drones become idle
        for d in available:
            assigned[d] = idle_group

        # Finalize assignments: ensure group name is valid, else fallback to idle, and call environment.assign_group
        for comp in components:
            group = assigned.get(comp, idle_group)
            if group not in group_ids:
                group = idle_group
            environment.assign_group(comp, group)