from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    """
    Adaptation that always fully protects the single field with the highest threat level
    using the closest drones until the field's drones_for_full_protection requirement is met.
    All other drones are assigned to 'idle'. Every component is explicitly reassigned each step.
    """
    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper to ensure we use only valid group ids
        def valid_group(name):
            return name if name in group_ids else "idle"

        # Gather threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no fields need protection, assign all drones to idle
        if not threatened_fields:
            idle_group = valid_group("idle")
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Choose the field with highest threat_level
        top_field = max(threatened_fields, key=lambda f: f.threat_level)
        protect_group_name = valid_group(f"protecting {top_field.id}")
        idle_group = valid_group("idle")

        # Helper: compute distance from drone to field center
        def field_center_distance(comp, field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            dx = getattr(comp.location, "x", 0) - cx
            dy = getattr(comp.location, "y", 0) - cy
            return math.hypot(dx, dy)

        required = int(getattr(top_field, "drones_for_full_protection", 0))

        # Partition drones by current state and target
        protecting_current = [c for c in components if getattr(c, "state", "") == "protecting" and getattr(c, "target_id", None) == top_field.id]
        moving_to_target = [c for c in components if getattr(c, "state", "") == "moving_to_field" and getattr(c, "target_id", None) == top_field.id]
        # remaining drones (neither protecting nor moving-to this field)
        remaining = [c for c in components if c not in protecting_current and c not in moving_to_target]

        # Build set of drones to assign to protecting group.
        # Keep all currently protecting drones (do not evict them).
        selected_protecting = list(protecting_current)

        # If we still need more drones to reach required, add movers then closest remaining drones.
        if len(selected_protecting) < required:
            # use movers next
            need = required - len(selected_protecting)
            to_add_from_movers = moving_to_target[:need]
            selected_protecting.extend(to_add_from_movers)

            # if still need more, choose closest from remaining
            if len(selected_protecting) < required:
                need = required - len(selected_protecting)
                # sort remaining by distance to field center
                remaining_sorted = sorted(remaining, key=lambda c: field_center_distance(c, top_field))
                selected_protecting.extend(remaining_sorted[:need])

        # Convert to a set for fast membership tests (object identity)
        selected_set = set(selected_protecting)

        # Finally assign groups for all components:
        # - selected_set -> protecting {field.id}
        # - everyone else -> idle
        for comp in components:
            if comp in selected_set:
                environment.assign_group(comp, protect_group_name)
            else:
                environment.assign_group(comp, idle_group)