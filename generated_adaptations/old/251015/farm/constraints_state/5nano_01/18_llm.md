```py
"""
Greedy top-down protection with deterministic full-top-first approach.

Goal:
- Always try to fully protect the currently most threatened field (top_field) using
  the closest available drones.
- If top_field cannot be fully protected due to limited drones, protect as much as possible.
- Then allocate remaining drones to other threatened fields in descending threat order,
  again using the closest drones first.
- Any drone not assigned to a protecting group becomes idle.
"""

from math import hypot

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0]
        if not threatened:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort threats high -> low
        threatened.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)
        top_field = threatened[0]
        top_id = top_field.id

        # Mapping of drone -> group
        final_group = {}

        def assign(d, grp):
            if d not in final_group:
                final_group[d] = grp

        # 1) Pre-assign drones already heading to top
        for c in components:
            st = getattr(c, "state", "")
            tid = getattr(c, "target_id", None)
            if tid == top_id and st in ("moving_to_field", "protecting"):
                assign(c, f"protecting {top_id}")

        # Helper: current protection for a field (top or others)
        def current_protection(field):
            fid = field.id
            cur = getattr(field, "protecting_drones", 0) + getattr(field, "arriving_drones", 0)
            cur += sum(1 for d, g in final_group.items() if g == f"protecting {fid}")
            return cur

        # 2) Fully/properly protect top_field if possible
        full_top = int(getattr(top_field, "drones_for_full_protection", 1))
        current_top = current_protection(top_field)
        needed_top = max(0, full_top - current_top)

        if needed_top > 0:
            cx = (getattr(top_field, "left", 0) + getattr(top_field, "right", 0)) / 2.0
            cy = (getattr(top_field, "top", 0) + getattr(top_field, "bottom", 0)) / 2.0

            candidates = []
            for c in components:
                if c in final_group:
                    continue
                loc = getattr(c, "location", None)
                if loc is None:
                    continue
                dx = getattr(loc, "x", 0.0) - cx
                dy = getattr(loc, "y", 0.0) - cy
                dist = hypot(dx, dy)
                candidates.append((dist, c))
            candidates.sort(key=lambda t: t[0])

            for _, c in candidates[:needed_top]:
                assign(c, f"protecting {top_id}")

        # 3) After top, allocate to other threatened fields in threat order
        remaining_fields = [f for f in threatened if f.id != top_id]
        remaining_fields.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)

        for f in remaining_fields:
            fid = f.id
            full = int(getattr(f, "drones_for_full_protection", 1))
            current = current_protection(f)
            needed = max(0, full - current)
            if needed <= 0:
                continue

            cx = (getattr(f, "left", 0) + getattr(f, "right", 0)) / 2.0
            cy = (getattr(f, "top", 0) + getattr(f, "bottom", 0)) / 2.0

            candidates = []
            for c in components:
                if c in final_group:
                    continue
                loc = getattr(c, "location", None)
                if loc is None:
                    continue
                dx = getattr(loc, "x", 0.0) - cx
                dy = getattr(loc, "y", 0.0) - cy
                dist = hypot(dx, dy)
                candidates.append((dist, c))
            candidates.sort(key=lambda t: t[0])

            for _, c in candidates[:needed]:
                assign(c, f"protecting {fid}")

        # 4) Idle any drones not assigned yet
        for c in components:
            if c not in final_group:
                final_group[c] = "idle"

        # 5) Apply assignments
        for c, grp in final_group.items():
            environment.assign_group(c, grp)
```