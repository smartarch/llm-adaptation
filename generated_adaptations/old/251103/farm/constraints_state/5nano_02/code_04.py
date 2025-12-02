import math
from generated_adaptations.base_classes.farm import FarmAdaptation as BaseFarmAdaptation

class SmartFarmAdaptation(BaseFarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify fields with any bird threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not threat_fields:
            # No threat: idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Choose the field with the highest threat level
        top_field = max(threat_fields, key=lambda f: f.threat_level)
        top_id = top_field.id

        # How many drones are currently protecting the top field (including arriving)
        eff_prot = getattr(top_field, "protecting_drones", 0) + getattr(top_field, "arriving_drones", 0)
        full_needed = getattr(top_field, "drones_for_full_protection", 0)
        need = max(0, full_needed - eff_prot)

        # If need > 0, reinforce using non-top-field drones with preference for idle ones
        chosen_for_top = set()

        # If we need reinforcement, select drones
        if need > 0:
            # Prepare candidate pools
            idle_candidates = []
            non_idle_candidates = []

            # Distances to top field center
            cx = (top_field.left + top_field.right) / 2.0
            cy = (top_field.top + top_field.bottom) / 2.0

            for d in components:
                # Already protecting the top field: keep them in place (do not consider as reinforcement candidates)
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_id:
                    continue

                dist = float('inf')
                loc = getattr(d, "location", None)
                if loc is not None:
                    dist = math.hypot(loc.x - cx, loc.y - cy)

                # Classify as idle or not
                if getattr(d, "state", None) == "idle":
                    idle_candidates.append((dist, d))
                else:
                    # Not idle: consider as potential reinforcement (moves to protect top_field)
                    non_idle_candidates.append((dist, d))

            # Sort by distance (closest first)
            idle_candidates.sort(key=lambda t: t[0])
            non_idle_candidates.sort(key=lambda t: t[0])

            # Take from idle first, then from non-idle if needed
            take_from_idle = min(need, len(idle_candidates))
            for i in range(take_from_idle):
                _, drone = idle_candidates[i]
                chosen_for_top.add(drone)

            remaining_need = need - take_from_idle
            if remaining_need > 0:
                for i in range(min(remaining_need, len(non_idle_candidates))):
                    _, drone = non_idle_candidates[i]
                    chosen_for_top.add(drone)

        # After selecting reinforcement, assign groups
        # First, assign reinforcement drones to the top field protection
        for d in components:
            if d in chosen_for_top:
                environment.assign_group(d, f"protecting {top_id}")

        # For the rest, preserve existing protections to minimize thrash
        for d in components:
            if d in chosen_for_top:
                continue
            st = getattr(d, "state", None)
            tid = getattr(d, "target_id", None)

            if st == "protecting" and tid is not None:
                # Keep protecting the field they're currently targeting
                environment.assign_group(d, f"protecting {tid}")
            elif st == "idle" or tid is None:
                environment.assign_group(d, "idle")
            else:
                # Moving to a field (or other transient state) map to protecting its target
                environment.assign_group(d, f"protecting {tid}")