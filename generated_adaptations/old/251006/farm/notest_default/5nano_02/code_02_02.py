"""
Smart adaptation: multi-field priority-based protection with continuity.

Goals:
- Protect multiple fields proportionally to their threat and current protection.
- Keep drones already protecting a field if that field still needs protection.
- Move drones only to fill remaining protection needs, in order of priority.
- If no fields are threatened, all drones become idle.
"""

from typing import List
import abc

# Import the base adaptation class
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        """
        Assign drones (components) to groups based on a multi-field priority strategy.
        - Idle drones go to "idle".
        - Drones are assigned to "protecting {field.id}" groups where the field has threat.
        """

        # Collect fields with positive threat levels
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not fields_with_threat:
            # No threat: all drones idle
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Map field id to field object for quick access
        fields_by_id = {f.id: f for f in fields_with_threat}

        # Determine required drones for full protection per field
        required_per_field = {}
        for f in fields_with_threat:
            req = int(getattr(f, "drones_for_full_protection", len(components)))
            if req < 0:
                req = 0
            required_per_field[f.id] = req

        # Count currently protecting drones per field
        protecting_counts = {fid: 0 for fid in required_per_field.keys()}
        for c in components:
            if getattr(c, "state", None) == "protecting":
                fid = getattr(c, "target_id", None)
                if fid in protecting_counts:
                    protecting_counts[fid] += 1

        # Remaining protection needed per field
        remaining_per_field = {}
        for fid, req in required_per_field.items():
            rem = max(0, req - protecting_counts.get(fid, 0))
            remaining_per_field[fid] = rem

        # If a field has no remaining protection need, its priority is 0
        # Compute priority per field: threat_level * (1 - current_protection_ratio)
        priorities = []
        for fid, rem in remaining_per_field.items():
            if rem <= 0:
                pr = 0.0
            else:
                f = fields_by_id[fid]
                threat = getattr(f, "threat_level", 0.0)
                req = max(1, required_per_field[fid])
                current = protecting_counts.get(fid, 0)
                ratio = min(1.0, current / req)
                pr = threat * (1.0 - ratio)
            priorities.append((pr, fid))
        priorities.sort(reverse=True)  # highest priority first

        # Step 1: Keep drones that are already protecting a field that still needs protection
        assigned_set = set()  # track drones we explicitly assigned
        for c in components:
            if getattr(c, "state", None) == "protecting":
                fid = getattr(c, "target_id", None)
                if fid in remaining_per_field and remaining_per_field[fid] > 0:
                    gid = f"protecting {fid}"
                    if gid in group_ids:
                        environment.assign_group(c, gid)
                        assigned_set.add(id(c))
                        # Decrement remaining for this field
                        remaining_per_field[fid] -= 1
                    else:
                        environment.assign_group(c, "idle")
                        assigned_set.add(id(c))
                else:
                    # This drone's current field no longer needs protection
                    environment.assign_group(c, "idle")
                    assigned_set.add(id(c))

        # Step 2: Allocate remaining drones to fields by priority
        unassigned = [c for c in components if id(c) not in assigned_set]

        for pr, fid in priorities:
            if pr <= 0:
                continue
            need = remaining_per_field.get(fid, 0)
            if need <= 0:
                continue
            gid = f"protecting {fid}"
            if gid not in group_ids:
                continue  # cannot assign if group not available

            i = 0
            while i < len(unassigned) and need > 0:
                c = unassigned.pop(i)
                environment.assign_group(c, gid)
                need -= 1
                remaining_per_field[fid] = need
                # Do not increment i since we removed this element
            if not unassigned:
                break

        # Step 3: Any remaining drones become idle
        for c in unassigned:
            environment.assign_group(c, "idle")