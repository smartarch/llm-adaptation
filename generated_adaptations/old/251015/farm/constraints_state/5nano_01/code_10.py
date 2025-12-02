"""
Adaptive strategy update (robust single-assignment version):

- Build a final mapping of each drone to exactly one group.
- Prioritize the most threatened field and fully protect it with the closest available drones.
- Drones already heading to the top field count toward protection.
- After top field, iteratively protect other threatened fields in threat order.
- Any drone not assigned to a protecting group becomes idle.
"""

from math import hypot

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather threatened fields (threat_level > 0)
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0]
        if not threatened:
            # No threat: idle all drones
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort threatened fields by threat level (highest first)
        threatened.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)
        top_field = threatened[0]
        top_id = top_field.id

        final_group = {}  # drone -> group
        def assign(c, grp):
            if c not in final_group:
                final_group[c] = grp

        # Step A: pre-existing heading drones to the top field
        for c in components:
            st = getattr(c, "state", "")
            tid = getattr(c, "target_id", None)
            if tid == top_id and st in ("moving_to_field", "protecting"):
                assign(c, f"protecting {top_id}")

        # Step B: compute needed for top field
        current_top = (
            sum(1 for d, g in final_group.items() if g == f"protecting {top_id}")
            + getattr(top_field, "protecting_drones", 0)
            + getattr(top_field, "arriving_drones", 0)
        )
        full_top = int(getattr(top_field, "drones_for_full_protection", 1))
        needed_top = max(0, full_top - current_top)

        # Step C: assign closest unassigned drones to top if needed
        if needed_top > 0:
            center_x = (getattr(top_field, "left", 0) + getattr(top_field, "right", 0)) / 2.0
            center_y = (getattr(top_field, "top", 0) + getattr(top_field, "bottom", 0)) / 2.0

            candidates = []
            for c in components:
                if c in final_group:
                    continue
                loc = getattr(c, "location", None)
                if loc is None:
                    continue
                dx = getattr(loc, "x", 0.0) - center_x
                dy = getattr(loc, "y", 0.0) - center_y
                dist = hypot(dx, dy)
                candidates.append((dist, c))
            candidates.sort(key=lambda t: t[0])

            for dist, c in candidates[:needed_top]:
                assign(c, f"protecting {top_id}")

        # Step D: Other threatened fields in threat order
        remaining_fields = [f for f in threatened if f.id != top_id]
        remaining_fields.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)

        for f in remaining_fields:
            fid = f.id
            current = getattr(f, "protecting_drones", 0) + getattr(f, "arriving_drones", 0)
            current += sum(1 for g in final_group.values() if g == f"protecting {fid}")
            full = int(getattr(f, "drones_for_full_protection", 1))
            needed = max(0, full - current)
            if needed <= 0:
                continue

            center_x = (getattr(f, "left", 0) + getattr(f, "right", 0)) / 2.0
            center_y = (getattr(f, "top", 0) + getattr(f, "bottom", 0)) / 2.0

            candidates = []
            for c in components:
                if c in final_group:
                    continue
                loc = getattr(c, "location", None)
                if loc is None:
                    continue
                dx = getattr(loc, "x", 0.0) - center_x
                dy = getattr(loc, "y", 0.0) - center_y
                dist = hypot(dx, dy)
                candidates.append((dist, c))
            candidates.sort(key=lambda t: t[0])

            for dist, c in candidates[:needed]:
                assign(c, f"protecting {fid}")

        # Step E: Idle all drones not assigned
        for c in components:
            if c not in final_group:
                final_group[c] = "idle"

        # Step F: Apply the assignments
        for c, grp in final_group.items():
            environment.assign_group(c, grp)