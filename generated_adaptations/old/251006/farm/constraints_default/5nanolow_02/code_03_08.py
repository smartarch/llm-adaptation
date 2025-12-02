# Final fix: robust group validation to avoid assignment errors
# - Ensure we never assign a drone to a group not present in group_ids.
# - If the top-field protecting group ("protecting <top_id>") is not in group_ids, fall back
#   to the first valid group in group_ids. If none, use "idle".
# - Keep the rest of the logic intact: preserve drones already protecting, then allocate
#   to top field, then to others, always respecting valid groups.

from typing import List

from generated_adaptations.base_classes.farm import FarmAdaptation  # type: ignore

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _valid_group(self, name: str, group_ids: List[str]) -> bool:
        return name in group_ids

    def _field_sort_key(self, f):
        threat = float(getattr(f, "threat_level", 0.0))
        fid = getattr(f, "id", "")
        import re
        m = re.search(r'(\d+)$', str(fid))
        num = int(m.group(1)) if m else 0
        return (threat, num)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        # Identify threatened fields
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0]
        fields_with_threat.sort(key=self._field_sort_key, reverse=True)
        if not fields_with_threat:
            for c in components:
                grp = "idle" if self._valid_group("idle", group_ids) else (group_ids[0] if group_ids else "idle")
                environment.assign_group(c, grp)
            return

        top_field = fields_with_threat[0]
        top_id = top_field.id
        # Current protectors of top field
        current_top = sum(1 for c in components if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_id)
        # Drones required for full protection
        required = 0
        try:
            required = int(getattr(top_field, "drones_for_full_protection", 0))
        except Exception:
            required = 0
        needs_top = max(0, required - current_top)

        # Determine the desired group name for top protection; validate against group_ids
        top_group = f"protecting {top_id}"
        if not self._valid_group(top_group, group_ids):
            top_group = group_ids[0] if group_ids else "idle"

        # Build per-drone plan (one assignment per drone)
        desired_groups = [None] * len(components)

        # Step A: keep drones already protecting in their current group (if valid)
        for i, c in enumerate(components):
            if getattr(c, "state", None) == "protecting":
                fid = getattr(c, "target_id", None)
                grp = f"protecting {fid}" if fid is not None else None
                if grp and self._valid_group(grp, group_ids):
                    desired_groups[i] = grp
                else:
                    desired_groups[i] = "idle"

        # Step B: assign unassigned drones to top field if possible
        unassigned = [i for i, g in enumerate(desired_groups) if g is None]
        while needs_top > 0 and unassigned:
            idx = unassigned.pop(0)
            desired_groups[idx] = top_group
            needs_top -= 1

        # Step C: assign remaining unassigned drones to next most-threatened fields (optional, simple)
        for f in fields_with_threat[1:]:
            fid = f.id
            grp = f"protecting {fid}"
            if not self._valid_group(grp, group_ids):
                continue
            required = 0
            try:
                required = int(getattr(f, "drones_for_full_protection", 0))
            except Exception:
                required = 0
            current = sum(1 for c in components if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == fid)
            need = max(0, required - current)
            while need > 0 and unassigned:
                idx = unassigned.pop(0)
                desired_groups[idx] = grp
                need -= 1

        # Step D: remaining drones idle
        for idx in unassigned:
            desired_groups[idx] = "idle"

        # Step E: apply assignments; ensure every drone has a valid group
        for c, grp in zip(components, desired_groups):
            if grp is None:
                grp = "idle" if self._valid_group("idle", group_ids) else (group_ids[0] if group_ids else "idle")
            environment.assign_group(c, grp)