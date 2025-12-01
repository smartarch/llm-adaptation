from math import sqrt
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat level
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Pre-compute centers for each field
        centers = {}
        for f in threat_fields:
            centers[f.id] = ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        # Process fields in descending order of threat
        threat_fields_sorted = sorted(
            threat_fields, key=lambda ff: getattr(ff, "threat_level", 0), reverse=True
        )

        plan = {}        # index -> target group
        allocated = set()  # indices already allocated in this decision

        for f in threat_fields_sorted:
            center = centers[f.id]
            field_group = f"protecting {f.id}"

            # Current protectors for this field
            current_protect = [
                i for i, c in enumerate(components)
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id
            ]
            for idx in current_protect:
                plan[idx] = field_group
                allocated.add(idx)

            current_count = len(current_protect)
            needed = int(getattr(f, "drones_for_full_protection", 0)) - current_count
            if needed <= 0:
                continue

            # Find nearest available drones to this field's center
            candidates = [i for i in range(len(components)) if i not in allocated]
            dist_list = []
            cx, cy = center
            for idx in candidates:
                loc = getattr(components[idx], "location", None)
                if loc is None or getattr(loc, "x", None) is None or getattr(loc, "y", None) is None:
                    d = float("inf")
                else:
                    dx = loc.x - cx
                    dy = loc.y - cy
                    d = (dx * dx + dy * dy) ** 0.5
                dist_list.append((d, idx))
            dist_list.sort(key=lambda t: t[0])

            # Allocate up to 'needed' drones from the closest candidates
            for _, idx in dist_list[:max(needed, 0)]:
                plan[idx] = field_group
                allocated.add(idx)

        # Now assign groups to all drones
        for i in range(len(components)):
            if i in plan:
                environment.assign_group(components[i], plan[i])
            else:
                environment.assign_group(components[i], "idle")