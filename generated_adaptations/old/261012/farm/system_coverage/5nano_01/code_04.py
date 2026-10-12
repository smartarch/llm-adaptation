from typing import List
import math

# The base class is assumed to be importable as described
from generated_adaptations.base_classes.farm import FarmAdaptation  # type: ignore

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        # Gather fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # Sort fields by decreasing threat, then by id for deterministic ordering
        threat_fields_sorted = sorted(threat_fields, key=lambda f: (-f.threat_level, f.id))

        assignments = {}  # component -> group_id

        if threat_fields_sorted:
            # Build a priority map: field_id -> priority index
            field_priority = {f.id: i for i, f in enumerate(threat_fields_sorted)}

            # 1) Top field: fully protect using closest drones (including reallocation from other drones if needed)
            top_field = threat_fields_sorted[0]
            top_group = f"protecting {top_field.id}"

            # Ensure current protectors of the top field stay in place
            current_top_protectors = [
                c for c in components
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id
            ]
            for c in current_top_protectors:
                assignments[c] = top_group

            required = int(getattr(top_field, "drones_for_full_protection", 0))
            current_top_count = len(current_top_protectors)
            needed = max(0, required - current_top_count)

            if needed > 0:
                cx = (top_field.left + top_field.right) / 2.0
                cy = (top_field.top + top_field.bottom) / 2.0

                # Candidate pool: all drones not already assigned to top_field, with reallocation allowed
                candidates = []
                for c in components:
                    if c in assignments:
                        continue
                    loc = getattr(c, "location", None)
                    dist2 = float("inf")
                    if loc is not None:
                        dx = loc.x - cx
                        dy = loc.y - cy
                        dist2 = dx*dx + dy*dy
                    candidates.append((dist2, c))

                # Sort by distance and pick needed drones
                candidates.sort(key=lambda t: t[0])
                for dist2, d in candidates[:needed]:
                    assignments[d] = top_group

            # 2) Additional fields (in threat order) -> try to fully protect using remaining (idle first, then lower-priority reallocation)
            # Build a quick map of threat field id to its group
            # Start from second field (index 1)
            for i, f in enumerate(threat_fields_sorted[1:], start=1):
                grp = f"protecting {f.id}"
                # Current protectors for this field
                current_protectors = [
                    c for c in components
                    if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id
                ]
                current_count = len(current_protectors)
                needed = max(0, int(getattr(f, "drones_for_full_protection", 0)) - current_count)

                # If already full, ensure current protectors are in correct group
                for c in current_protectors:
                    assignments[c] = grp

                if needed <= 0:
                    continue

                cx = (f.left + f.right) / 2.0
                cy = (f.top + f.bottom) / 2.0

                # Build candidate pool with priority rules:
                # - Prefer idle drones
                # - If not enough idle, consider reallocation from lower-priority fields (idx > i)
                candidates = []
                for c in components:
                    if c in assignments:
                        continue
                    # Determine if we are allowed to steal from this drone's current field
                    allow = True
                    if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) is not None:
                        t_id = c.target_id
                        pid = field_priority.get(t_id, 9999)
                        if pid < i:
                            # This drone is protecting a higher-priority field; avoid stealing
                            allow = False
                    if not allow:
                        continue

                    loc = getattr(c, "location", None)
                    dist2 = float("inf")
                    if loc is not None:
                        dx = loc.x - cx
                        dy = loc.y - cy
                        dist2 = dx*dx + dy*dy
                    candidates.append((dist2, c))

                # Sort by distance and pick needed drones
                candidates.sort(key=lambda t: t[0])
                for dist2, d in candidates[:needed]:
                    assignments[d] = grp

        # 3) Any drone not assigned yet -> idle
        for c in components:
            if c not in assignments:
                assignments[c] = "idle"

        # Apply group assignments
        for comp, group_id in assignments.items():
            environment.assign_group(comp, group_id)