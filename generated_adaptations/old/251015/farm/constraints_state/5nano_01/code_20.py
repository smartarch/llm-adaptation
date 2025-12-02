"""
Greedy top-down protection with deterministic full-top-first approach.

This version adds a defensive guard to ensure we never assign a drone to a
group name that isn't present in the provided group_ids. If the intended
protecting group isn't valid, we fall back to idle for that drone. This
eliminates potential "assignment errors" while preserving the intended
protection strategy when possible.
"""

from math import hypot
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Collect threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0]
        if not threatened:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # 2) Sort threats high to low
        threatened.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)
        top_field = threatened[0]
        top_id = top_field.id

        final_group = {}

        def assign(d, grp):
            # Guard against invalid group names
            if grp not in group_ids:
                grp = "idle"
            if d not in final_group:
                final_group[d] = grp

        # 3) Pre-assign drones already heading to the top field
        for c in components:
            st = getattr(c, "state", "")
            tid = getattr(c, "target_id", None)
            if tid == top_id and st in ("moving_to_field", "protecting"):
                assign(c, f"protecting {top_id}")

        # 4) Helper to compute current protection for a field
        def current_protection(field):
            fid = field.id
            cur = getattr(field, "protecting_drones", 0) + getattr(field, "arriving_drones", 0)
            cur += sum(1 for d, g in final_group.items() if g == f"protecting {fid}")
            return cur

        # 5) Try to fully/properly protect top_field
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

            for dist, c in candidates[:needed_top]:
                assign(c, f"protecting {top_id}")

            # Fallback: best-effort extra drones if still not enough
            if sum(1 for g in final_group.values() if g == f"protecting {top_id}") < full_top:
                remaining_needed = full_top - sum(1 for g in final_group.values() if g == f"protecting {top_id}")
                for dist, c in candidates[len(candidates[:needed_top:]):]:
                    if remaining_needed <= 0:
                        break
                    assign(c, f"protecting {top_id}")
                    remaining_needed -= 1
                if remaining_needed > 0:
                    for c in components:
                        if c in final_group:
                            continue
                        assign(c, f"protecting {top_id}")
                        remaining_needed -= 1
                        if remaining_needed <= 0:
                            break

        # 6) After top, allocate to other threatened fields in threat order
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

            if sum(1 for g in final_group.values() if g == f"protecting {fid}") < full:
                remaining_needed = full - sum(1 for g in final_group.values() if g == f"protecting {fid}")
                for c in components:
                    if c in final_group:
                        continue
                    assign(c, f"protecting {fid}")
                    remaining_needed -= 1
                    if remaining_needed <= 0:
                        break

        # 7) Idle any drones not assigned
        for c in components:
            if c not in final_group:
                final_group[c] = "idle"

        # 8) Apply assignments
        for c, grp in final_group.items():
            environment.assign_group(c, grp)