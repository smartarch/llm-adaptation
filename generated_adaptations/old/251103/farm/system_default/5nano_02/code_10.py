"""
Robust one-pass assignment strategy:
- Compute a set of valid protection groups for fields with threat > 0.
- Identify the top-threat field that has a valid protection group.
- Allocate drones to fully protect the top field using nearest drones first.
- Then allocate additional drones to other threatened fields (with valid groups) by proximity while preserving existing protections.
- Finally, assign any remaining drones to either their current target's protection group (if valid) or idle.
- All drones are assigned exactly once per step.
"""

from typing import List
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        fields = getattr(environment, "fields", [])
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # Build a map of valid protection groups for fields with threat
        valid_protection_for_field = {}
        for f in threat_fields:
            gid = f"protecting {f.id}"
            if gid in group_ids:
                valid_protection_for_field[f.id] = gid

        # If there is no threat or no valid protection groups exist, idle everyone
        if not threat_fields or not valid_protection_for_field:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threat fields by threat level (high to low)
        threat_fields_sorted = sorted(
            threat_fields, key=lambda f: getattr(f, "threat_level", 0), reverse=True
        )

        # Pick top field that has a valid protection group
        top_field = None
        for f in threat_fields_sorted:
            if f.id in valid_protection_for_field:
                top_field = f
                break

        if top_field is None:
            for d in components:
                environment.assign_group(d, "idle")
            return

        top_group = valid_protection_for_field[top_field.id]
        required = int(getattr(top_field, "drones_for_full_protection", 1))

        # Step 1: drones currently heading to or protecting the top field
        current_top = [
            d for d in components
            if d.state in ("protecting", "moving_to_field")
            and getattr(d, "target_id", None) == top_field.id
        ]
        assigned_ids = set(id(d) for d in current_top)

        final_group = {}

        # Assign current top drones to top_group
        for d in current_top:
            final_group[id(d)] = top_group

        # Step 2: fill the gap to full protection with nearest drones
        if len(current_top) < required:
            need = required - len(current_top)
            cx = (getattr(top_field, "left", 0) + getattr(top_field, "right", 0)) / 2.0
            cy = (getattr(top_field, "top", 0) + getattr(top_field, "bottom", 0)) / 2.0

            candidates = []
            for d in components:
                if id(d) in assigned_ids:
                    continue
                lx = getattr(d.location, "x", 0)
                ly = getattr(d.location, "y", 0)
                dx = lx - cx
                dy = ly - cy
                dist2 = dx * dx + dy * dy
                candidates.append((dist2, d))

            candidates.sort(key=lambda t: t[0])
            for _, d in candidates[:need]:
                final_group[id(d)] = top_group
                assigned_ids.add(id(d))

        # Step 3: allocate remaining drones to other threatened fields with valid groups
        # Also preserve existing protections by assigning drones currently heading toward those fields
        for field in threat_fields_sorted:
            if field.id == top_field.id:
                continue
            if field.id not in valid_protection_for_field:
                continue
            field_group = valid_protection_for_field[field.id]

            # Current drones heading toward this field
            current_for_field = [
                d for d in components
                if d.state in ("protecting", "moving_to_field")
                and getattr(d, "target_id", None) == field.id
            ]
            # If not yet assigned, assign them to this field_group
            for d in current_for_field:
                if id(d) not in final_group:
                    final_group[id(d)] = field_group
                    assigned_ids.add(id(d))

            need = int(getattr(field, "drones_for_full_protection", 1)) - len(current_for_field)
            if need <= 0:
                continue

            cx = (getattr(field, "left", 0) + getattr(field, "right", 0)) / 2.0
            cy = (getattr(field, "top", 0) + getattr(field, "bottom", 0)) / 2.0

            remaining = [d for d in components if id(d) not in assigned_ids]
            candidates = []
            current_for_field_ids = set(id(d) for d in current_for_field)
            for d in remaining:
                if id(d) in current_for_field_ids:
                    continue
                lx = getattr(d.location, "x", 0)
                ly = getattr(d.location, "y", 0)
                dx = lx - cx
                dy = ly - cy
                dist2 = dx * dx + dy * dy
                candidates.append((dist2, d))

            candidates.sort(key=lambda t: t[0])
            for _, d in candidates[:max(need, 0)]:
                final_group[id(d)] = field_group
                assigned_ids.add(id(d))

        # Step 4: Assign any drone not yet assigned
        for d in components:
            if id(d) in assigned_ids:
                continue
            t = getattr(d, "target_id", None)
            if t is not None:
                grp = f"protecting {t}"
                if grp in group_ids:
                    final_group[id(d)] = grp
                    assigned_ids.add(id(d))
                    continue
            # Fallback to idle
            final_group[id(d)] = "idle"
            assigned_ids.add(id(d))

        # Step 5: Apply assignments (exactly one per drone)
        for d in components:
            gid = final_group.get(id(d), "idle")
            environment.assign_group(d, gid)