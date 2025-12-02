```py
"""
Improved adaptation strategy (robust to group availability):
- Prioritize fully protecting the top-threat field, but only using protection groups that actually exist.
- If some fields do not have a valid "protecting <field_id>" group, they are skipped for protection to avoid
  invalid group assignments.
- Drones are assigned exactly once per step:
  - Drones allocated to the top field are assigned to "protecting <top_field.id>".
  - Remaining drones are allocated to other threatened fields that have valid protection groups, using nearest
    drones first to fill the required protection.
  - All other drones are finally assigned to either their current valid protection target (if such a group exists)
    or to "idle".
- This preserves existing protections when possible and avoids invalid group names.

This implementation adheres to the required interface and avoids assigning any drone to multiple groups in a single step.
"""

from typing import List
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        components: list of drone components
        environment: environment providing fields and assign_group
        group_ids: list of all valid group names
        step: current timestep (unused in this strategy but kept for compatibility)
        """
        # Build a quick lookup for valid protection groups
        valid_protection_for_field = {}
        for f in getattr(environment, "fields", []):
            if getattr(f, "threat_level", 0) > 0:
                gid = f"protecting {f.id}"
                if gid in group_ids:
                    valid_protection_for_field[f.id] = gid

        threat_fields = [f for f in getattr(environment, "fields", []) if getattr(f, "threat_level", 0) > 0]
        # If no threats or no valid protection groups exist, idle all drones
        if not threat_fields or not valid_protection_for_field:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threat fields by threat_level (desc) to define priority order
        threat_fields_sorted = sorted(
            threat_fields, key=lambda f: getattr(f, "threat_level", 0), reverse=True
        )

        # Top field must also have a valid protection group
        top_field = None
        for f in threat_fields_sorted:
            if f.id in valid_protection_for_field:
                top_field = f
                break

        if top_field is None:
            # No top field with a valid group -> idle all
            for d in components:
                environment.assign_group(d, "idle")
            return

        top_group = valid_protection_for_field[top_field.id]

        # Number of drones needed for full protection (default to 1 if not provided)
        required = int(getattr(top_field, "drones_for_full_protection", 1))

        # Step 1: Drones currently heading to or protecting the top_field
        current_top = [
            d
            for d in components
            if d.state in ("protecting", "moving_to_field")
            and getattr(d, "target_id", None) == top_field.id
        ]
        assigned_ids = set(id(d) for d in current_top)

        # If not enough drones, pick nearest available drones to fill the gap
        if len(current_top) < required:
            need = required - len(current_top)

            # Center of the top field for distance calculation
            cx = (getattr(top_field, "left", 0) + getattr(top_field, "right", 0)) / 2.0
            cy = (getattr(top_field, "top", 0) + getattr(top_field, "bottom", 0)) / 2.0

            # Candidate drones not already assigned to top field
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
                environment.assign_group(d, top_group)
                assigned_ids.add(id(d))

        # Step 2: Distribute remaining drones to other threats with valid groups
        remaining = [d for d in components if id(d) not in assigned_ids]

        for field in threat_fields_sorted:
            if field.id == top_field.id:
                continue
            if field.id not in valid_protection_for_field:
                continue
            field_group = valid_protection_for_field[field.id]

            # Current protection for this field
            current_for_field = [
                d
                for d in components
                if d.state in ("protecting", "moving_to_field")
                and getattr(d, "target_id", None) == field.id
            ]
            need = int(getattr(field, "drones_for_full_protection", 1)) - len(current_for_field)
            if need <= 0:
                continue

            # Center of the field
            cx = (getattr(field, "left", 0) + getattr(field, "right", 0)) / 2.0
            cy = (getattr(field, "top", 0) + getattr(field, "bottom", 0)) / 2.0

            # Drones currently excluding top_field's assigned drones, and not already protecting this field
            current_for_field_ids = set(id(d) for d in current_for_field)

            candidates = []
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
                environment.assign_group(d, field_group)
                assigned_ids.add(id(d))

            # Update remaining after assignments
            remaining = [d for d in components if id(d) not in assigned_ids]

        # Step 3: Assign anyDrone not yet assigned
        # If a drone has a valid current target and that target has a protection group, assign to that
        # Otherwise, idle. This guarantees every drone is assigned exactly once.
        for d in components:
            if id(d) in assigned_ids:
                continue
            t = getattr(d, "target_id", None)
            if t is not None:
                grp = f"protecting {t}"
                if grp in group_ids:
                    environment.assign_group(d, grp)
                    assigned_ids.add(id(d))
                    continue
            # Fallback to idle
            environment.assign_group(d, "idle")
            assigned_ids.add(id(d))
```