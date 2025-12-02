# Strategy overview:
# - Identify the field with the highest threat level (>0). If none, keep all drones idle.
# - For the top-threat field, ensure it has full protection by allocating drones to the
#   group "protecting {field.id}".
# - Drones that are already protecting the top field are kept (they should remain in that group).
# - If more drones are needed to reach full protection, assign idle (or non-protecting) drones
#   to protect the top field until the field is fully protected.
# - All remaining drones are assigned to "idle".
#
# Rationale:
# - This aligns with the requirement to always fully protect the highest-threat field with the
#   closest available drones, and to keep existing protection if already at full protection.
# - We keep changes minimal: only assign additional drones to the top field and set others to idle.
#
# Notes:
# - We rely on the provided component attributes (state, target_id) to identify current protection.
# - We do not attempt to reallocate drones from a currently protected top field if it's already
#   fully protected.
# - If no field has threat_level > 0, all drones become idle.

from typing import List
import abc

# Import the base class from the provided path
try:
    from generated_adaptations.base_classes.farm import FarmAdaptation
except Exception:
    # If the module path differs in the environment, provide a minimal fallback
    class FarmAdaptation(abc.ABC):
        def __init__(self, **kwargs):
            pass

        @abc.abstractmethod
        def assign_drones(self, components, environment, group_ids, step: int):
            pass


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Step 1: Determine the top-threat field (threat_level > 0)
        fields = getattr(environment, "fields", []) or []
        top_field = None
        top_threat = -1.0

        # Collect fields with threat > 0
        candidate_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        if not candidate_fields:
            # No threat fields: send all drones to idle
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Find the field with the maximum threat level
        for f in candidate_fields:
            th = getattr(f, "threat_level", 0)
            if th > top_threat:
                top_threat = th
                top_field = f

        if top_field is None:
            # Should not happen, but guard anyway
            for d in components:
                environment.assign_group(d, "idle")
            return

        top_field_id = getattr(top_field, "id", None)
        # Validate field id
        if top_field_id is None:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Step 2: Identify current protection on the top field
        # Drones currently protecting this field
        current_protecting = []
        for idx, d in enumerate(components):
            state = getattr(d, "state", None)
            target = getattr(d, "target_id", None)
            if state == "protecting" and target == top_field_id:
                current_protecting.append(d)

        current_count = len(current_protecting)
        required = getattr(top_field, "drones_for_full_protection", 0)

        # Step 3: If currently fully protected, keep them as is; ensure others are idle
        allocated = set()
        for d in current_protecting:
            environment.assign_group(d, f"protecting {top_field_id}")
            allocated.add(id(d))

        # Step 4: If not enough drones, allocate additional idle/non-protecting drones
        if current_count < max(0, required - 0):
            need = max(0, required - current_count)
            if need > 0:
                for d in components:
                    if id(d) in allocated:
                        continue
                    # Check if this drone is already protecting another field; if so, skip for now
                    if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) is not None:
                        # This drone is protecting some other field; we won't move it in this step
                        continue
                    # Assign to protection of the top field
                    environment.assign_group(d, f"protecting {top_field_id}")
                    allocated.add(id(d))
                    need -= 1
                    if need <= 0:
                        break

        # Step 5: Make sure all remaining drones are idle
        for d in components:
            if id(d) in allocated:
                # Already assigned to protecting top field
                continue
            # If not yet assigned, set to idle
            environment.assign_group(d, "idle")