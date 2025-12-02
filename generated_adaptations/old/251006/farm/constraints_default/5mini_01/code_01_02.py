# Strategy and reasoning (described inline as comments)
#
# Task summary:
# - We have a fleet of drones (components) and several fields (environment.fields).
# - Fields have threat_level and a drones_for_full_protection count.
# - We must always fully protect the single field with the highest threat_level, using the
#   closest drones (and keeping drones already en route or protecting that field).
# - If the chosen field is already fully protected, keep the drones there.
# - Every component must be explicitly assigned to exactly one group each call,
#   using environment.assign_group(component, group_id).
# - Group names: "idle" and "protecting {field.id}" for fields with threat_level > 0.
#
# Adaptation strategy (high level):
# 1. Identify the field with the highest threat_level among environment.fields (only consider threat_level > 0).
#    If none, assign all drones to "idle".
# 2. For the chosen target field:
#    - Count drones that are already protecting it or moving to it (component.state == "protecting" or
#      (component.state == "moving_to_field" and component.target_id == field.id)). Treat both as already
#      committed to protect the field.
#    - If the committed count >= drones_for_full_protection, keep those drones assigned to
#      "protecting {field.id}" and assign all other drones to "idle".
#    - If committed count < required, pick the closest remaining drones (by Euclidean distance from drone
#      location to the field center) to fill the remaining slots. Assign these drones to the protecting group.
#    - Any drones not chosen for protecting the highest-threat field are assigned to "idle".
# 3. This ensures the highest-threat field receives the required number of (closest) drones. Drones that
#    were protecting other, lower-priority fields may be reassigned to the chosen field or to idle as needed.
#
# Notes on implementation details:
# - Use the field's center ((left+right)/2, (top+bottom)/2) to compute distances.
# - Carefully handle missing attributes defensively (but assume typical environment provides them).
# - Ensure the group names used match exactly "idle" and "protecting {field.id}" and exist in group_ids.
#
# The code below implements this strategy in the required class and method.

from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Prepare group names
        idle_group = "idle"

        # Build list of fields with positive threat
        fields_with_threat = [f for f in getattr(environment, "fields", []) if getattr(f, "threat_level", 0) > 0]

        # If no field has threat > 0 or idle group missing, assign all drones to idle (if valid)
        if not fields_with_threat or idle_group not in group_ids:
            for comp in components:
                # if idle group doesn't exist we still try to assign to idle; environment may handle invalid group names,
                # but spec says group_ids contains valid names, so this branch usually means no threats.
                environment.assign_group(comp, idle_group)
            return

        # Select the field with the highest threat_level. If tie, pick the one with largest threat_level then smallest id for determinism.
        def field_sort_key(f):
            # Negative id safe cast to str fallback
            return (getattr(f, "threat_level", 0), -hash(getattr(f, "id", "")))
        # choose max by threat_level
        target_field = max(fields_with_threat, key=lambda f: getattr(f, "threat_level", 0))

        protect_group_name = f"protecting {getattr(target_field, 'id')}"
        # If protect group name is not valid (defensive), fallback to idle-allocation
        if protect_group_name not in group_ids:
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Compute field center for distance calculations
        left = getattr(target_field, "left", 0.0)
        right = getattr(target_field, "right", 0.0)
        top = getattr(target_field, "top", 0.0)
        bottom = getattr(target_field, "bottom", 0.0)
        center_x = (left + right) / 2.0
        center_y = (top + bottom) / 2.0

        # Helper to compute distance from a component to the field center
        def comp_distance_to_field(comp):
            loc = getattr(comp, "location", None)
            if loc is None:
                return float("inf")
            x = getattr(loc, "x", 0.0)
            y = getattr(loc, "y", 0.0)
            return math.hypot(x - center_x, y - center_y)

        # Count drones already committed to the target field
        needed = int(getattr(target_field, "drones_for_full_protection", 0))

        already_committed = []
        others = []
        for comp in components:
            state = getattr(comp, "state", None)
            target_id = getattr(comp, "target_id", None)
            # Consider protecting or moving to the field as committed
            if (state == "protecting" and target_id == getattr(target_field, "id")) or \
               (state == "moving_to_field" and target_id == getattr(target_field, "id")):
                already_committed.append(comp)
            else:
                others.append(comp)

        committed_count = len(already_committed)

        # If not enough committed, select closest drones from others to fill the gap
        to_assign_protecting = list(already_committed)  # keep the committed ones
        if committed_count < needed:
            needed_more = needed - committed_count
            # Sort remaining drones by distance to the field center
            others_sorted = sorted(others, key=comp_distance_to_field)
            chosen = others_sorted[:needed_more]
            to_assign_protecting.extend(chosen)
            # Remove chosen from others so they won't be assigned to idle later
            remaining_others = [c for c in others if c not in chosen]
        else:
            # No additional needed; all non-committed drones will be idle
            remaining_others = others

        # Assign protecting group to chosen drones
        for comp in to_assign_protecting:
            environment.assign_group(comp, protect_group_name)

        # All other drones -> idle
        for comp in remaining_others:
            environment.assign_group(comp, idle_group)