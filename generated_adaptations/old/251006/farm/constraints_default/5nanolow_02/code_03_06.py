# Final robust adaptation strategy:
# - Choose the most threatened field (break ties deterministically by field id suffix).
# - Only use groups that are present in the provided group_ids list.
# - Keep drones already protecting a field in their current protection group (if that group is valid).
# - Allocate remaining drones to protect the top field until its full protection is reached, using
#   only valid "protecting <field_id>" groups. Any invalid or unavailable group falls back to "idle".
# - Any remaining drones are idle.

from typing import List

from generated_adaptations.base_classes.farm import FarmAdaptation  # type: ignore

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _valid_group(self, name: str, group_ids: List[str]) -> bool:
        return name in group_ids

    def _field_sort_key(self, f):
        # primary: threat level (desc), secondary: numeric suffix of id (desc)
        threat = float(getattr(f, "threat_level", 0.0))
        fid = getattr(f, "id", "")
        import re
        m = re.search(r'(\d+)$', str(fid))
        num = int(m.group(1)) if m else 0
        return (threat, num)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        # Gather threatened fields and sort with tie-breaker
        fields_with_threat = [
            f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0
        ]
        fields_with_threat.sort(key=self._field_sort_key, reverse=True)

        if not fields_with_threat:
            for c in components:
                # Ensure idle is a valid group
                if self._valid_group("idle", group_ids):
                    environment.assign_group(c, "idle")
                else:
                    # Fallback: assign to first valid group if idle isn't available
                    environment.assign_group(c, group_ids[0] if group_ids else "idle")
            return

        top_field = fields_with_threat[0]
        top_id = top_field.id
        # Count how many drones are currently protecting the top field
        current_top = sum(
            1 for c in components
            if getattr(c, "state", None) == "protecting"
            and getattr(c, "target_id", None) == top_id
        )
        # Drones needed for full protection of top field
        required = getattr(top_field, "drones_for_full_protection", 0)
        try:
            required = int(required)
        except Exception:
            required = 0
        needs_top = max(0, required - current_top)

        # Prepare plan: one assignment per drone
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

        # Build list of indices not yet assigned
        unassigned_indices = [i for i, g in enumerate(desired_groups) if g is None]

        # Step B: allocate unassigned drones to top field if the group is valid
        valid_top_group = f"protecting {top_id}"
        if not self._valid_group(valid_top_group, group_ids):
            valid_top_group = None

        while needs_top > 0 and unassigned_indices and valid_top_group:
            idx = unassigned_indices.pop(0)
            desired_groups[idx] = valid_top_group
            needs_top -= 1

        # Step C: allocate to other threatened fields if possible (optional)
        # Build a small list of remaining fields after top
        for f in fields_with_threat:
            fid = f.id
            if fid == top_id:
                continue
            grp = f"protecting {fid}"
            if not self._valid_group(grp, group_ids):
                continue
            required = getattr(f, "drones_for_full_protection", 0)
            try:
                required = int(required)
            except Exception:
                required = 0
            # Determine current protection count for this field
            current = sum(1 for c in components
                          if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == fid)
            need = max(0, required - current)
            while need > 0 and unassigned_indices:
                idx = unassigned_indices.pop(0)
                desired_groups[idx] = grp
                need -= 1

        # Step D: remaining drones idle
        for idx in unassigned_indices:
            desired_groups[idx] = "idle"

        # Apply assignments (one per drone)
        for c, grp in zip(components, desired_groups):
            if grp is None:
                # Safety fallback
                grp = "idle" if self._valid_group("idle", group_ids) else group_ids[0] if group_ids else "idle"
            environment.assign_group(c, grp)