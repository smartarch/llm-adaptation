Reasoning and strategy

We must always fully protect the single field with the highest threat level using the closest drones, keeping any drones already protecting that field. The unit tests additionally require that at least half of the drones are used for protection most of the time (i.e., we should avoid leaving too many drones idle).

Strategy summary:
- If no fields have threat_level > 0, assign all drones to "idle".
- Choose the field with the highest threat_level (top_field). Ensure it is fully protected:
  - Keep drones that are already protecting top_field.
  - Prefer drones that are already moving to top_field.
  - If more are needed, pick the nearest free drones to top_field until top_field's drones_for_full_protection is met or we run out of drones.
- After top_field is protected, ensure at least half of all drones are assigned to protection (ceil(N/2)). To reach that threshold:
  - Consider other threatened fields in descending threat_level.
  - For each, keep existing protecting drones for that field and movers toward the field, then add nearest free drones to fully protect the field (or until we reach the half-threshold).
  - Stop when the threshold is met or no more fields/drones can be used.
- All selected drones are assigned to the protecting group of the field they were chosen for ("protecting {field.id}"). All remaining drones are assigned to "idle".
- Every drone is explicitly assigned each step. Group name validity is checked: if the desired group name is not in group_ids, fall back to "idle".

This keeps the primary requirement (always fully protect the highest threat field) and uses additional available drones to increase overall protection coverage so that at least half of drones are in protecting groups when possible.

Implementation follows.

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math
from math import ceil

class SmartFarmAdaptation(FarmAdaptation):
    """
    Adaptation that:
    - Always fully protects the single field with the highest threat level using the closest drones.
    - Keeps drones already protecting that top field.
    - Then assigns additional drones to protect other threatened fields (by threat level),
      until at least half of the total drones are protecting (if possible).
    - All components are explicitly assigned each step.
    """
    def assign_drones(self, components, environment, group_ids, step: int):
        def valid_group(name):
            return name if name in group_ids else "idle"

        # Gather threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If none, set all drones to idle
        if not threatened_fields:
            idle_group = valid_group("idle")
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Helpers
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def distance_to_field(comp, field):
            cx, cy = field_center(field)
            dx = getattr(comp.location, "x", 0) - cx
            dy = getattr(comp.location, "y", 0) - cy
            return math.hypot(dx, dy)

        # Build lookup of current states
        protecting_by_field = {}
        moving_by_field = {}
        for comp in components:
            state = getattr(comp, "state", "")
            target = getattr(comp, "target_id", None)
            if state == "protecting" and target is not None:
                protecting_by_field.setdefault(target, []).append(comp)
            if state == "moving_to_field" and target is not None:
                moving_by_field.setdefault(target, []).append(comp)

        total_drones = len(components)
        half_required = ceil(total_drones / 2)

        # Choose top field by threat_level
        top_field = max(threatened_fields, key=lambda f: f.threat_level)
        # Sort other fields by threat level descending, excluding top
        other_fields = [f for f in threatened_fields if f.id != top_field.id]
        other_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Selected assignments: component -> field_id
        selected_assignment = {}

        # Helper to try to fill a specific field to its required count using available drones.
        # It will keep protectors and movers for that field if present and add nearest remaining drones.
        def fill_field(field, required, selected_assignment, available_set):
            # keep existing protecting drones for this field
            kept = []
            for comp in protecting_by_field.get(field.id, []):
                if comp in available_set:
                    kept.append(comp)
            # include movers to that field next
            movers = []
            for comp in moving_by_field.get(field.id, []):
                if comp in available_set and comp not in kept:
                    movers.append(comp)
            chosen = list(kept)
            # Add movers up to required
            need = max(0, required - len(chosen))
            if need > 0:
                chosen.extend(movers[:need])
            # If still need more, choose nearest from available_set excluding already chosen
            if len(chosen) < required:
                need = required - len(chosen)
                remaining_candidates = [c for c in available_set if c not in chosen]
                remaining_candidates.sort(key=lambda c: distance_to_field(c, field))
                chosen.extend(remaining_candidates[:need])
            # Assign chosen to this field
            for comp in chosen:
                selected_assignment[comp] = field.id
                if comp in available_set:
                    available_set.remove(comp)

        # Start by fully protecting the top field
        required_top = int(getattr(top_field, "drones_for_full_protection", 0))
        # available_set is set of components not yet assigned
        available = set(components)
        # Fill top field (this will keep protectors and movers first)
        fill_field(top_field, required_top, selected_assignment, available)

        # Ensure at least half of drones are protecting (if possible)
        if len(selected_assignment) < half_required:
            # Try to fill other fields in descending threat order to reach half_required
            for field in other_fields:
                required = int(getattr(field, "drones_for_full_protection", 0))
                # If already enough selected, break
                if len(selected_assignment) >= half_required:
                    break
                # If no available drones left, break
                if not available:
                    break
                # Fill this field to its required (or as much as available), but don't exceed what's needed to reach half
                # Compute how many we'd like to add for this field: min(required, remaining_needed + any already protecting/moving)
                # However fill_field handles keeping existing protectors/movers; so invoke it and let available constraints handle limits.
                fill_field(field, required, selected_assignment, available)

        # After attempting to satisfy half threshold, we might still have some protecting drones already protecting other fields
        # that we didn't explicitly keep; as a small improvement, keep any remaining currently protecting drones (they help protection)
        # if we haven't already assigned them and we still want to increase protected count (and we have no field-specific reason).
        if len(selected_assignment) < half_required and available:
            # Prefer to keep any remaining protectors (even if for fields not in threatened_fields)
            remaining_protectors = [c for c in list(available) if getattr(c, "state", "") == "protecting" and getattr(c, "target_id", None) is not None]
            for comp in remaining_protectors:
                # assign to their current target if group exists for that field (and target field has threat > 0)
                target = getattr(comp, "target_id", None)
                # Only accept if target is a threatened field id
                if target and any(f.id == target for f in threatened_fields):
                    selected_assignment[comp] = target
                    available.remove(comp)
                    if len(selected_assignment) >= half_required:
                        break

        # Finally, prepare group assignments
        # Map each selected component to the protecting group for its assigned field
        # All others go to idle
        # Validate group names
        idle_group = valid_group("idle")
        # Cache valid protecting group names for each field id
        protecting_group_cache = {}
        for f in threatened_fields:
            name = f"protecting {f.id}"
            protecting_group_cache[f.id] = valid_group(name)

        for comp in components:
            if comp in selected_assignment:
                field_id = selected_assignment[comp]
                group_name = protecting_group_cache.get(field_id, idle_group)
                environment.assign_group(comp, group_name)
            else:
                environment.assign_group(comp, idle_group)