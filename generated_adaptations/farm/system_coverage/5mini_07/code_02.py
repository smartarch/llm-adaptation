from typing import List
from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components: List[object], environment, group_ids, step: int):
        """
        Assign drones to groups according to the strategy described:
        - Fully protect the field with the highest threat_level (if any field has threat_level > 0).
        - Use drones already protecting or moving to that field as committed.
        - Choose additional drones by preference (idle/moving-other first, then protecting-other), and by distance.
        - Assign selected drones to "protecting {field.id}" and all others to "idle".
        """
        # Helper to compute Euclidean distance from a drone to a field center
        def distance_to_field_center(drone, field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            dx = getattr(drone.location, "x", 0) - cx
            dy = getattr(drone.location, "y", 0) - cy
            return math.hypot(dx, dy)
        
        # Prepare easy access to drones list
        drones = list(components)
        if not drones:
            return  # nothing to assign

        # Find fields with positive threat
        candidate_fields = [f for f in getattr(environment, "fields", []) if getattr(f, "threat_level", 0) > 0]

        # If no fields need protection, assign everyone to idle
        if not candidate_fields:
            idle_name = "idle"
            for d in drones:
                if idle_name in group_ids:
                    environment.assign_group(d, idle_name)
            return

        # Pick the single field with highest threat_level (tie-break by id for determinism)
        candidate_fields.sort(key=lambda f: (f.threat_level, str(f.id)), reverse=True)
        target_field = candidate_fields[0]
        target_group = f"protecting {target_field.id}"
        idle_group = "idle"

        # Ensure chosen group names are valid (fall back to idle if not)
        use_protect_group = target_group if target_group in group_ids else idle_group

        # Count already committed drones (protecting or moving_to_field with matching target_id)
        committed = []
        others = []
        for d in drones:
            if getattr(d, "target_id", None) == target_field.id and getattr(d, "state", "") in ("protecting", "moving_to_field"):
                committed.append(d)
            else:
                others.append(d)

        required = int(getattr(target_field, "drones_for_full_protection", 0))
        # Cap required by total number of drones available
        required = max(0, min(required, len(drones)))

        # If already enough committed, keep them and idle the rest
        needed = max(0, required - len(committed))

        selected_set = set(committed)  # final selected drones for protection

        if needed > 0:
            # Build a prioritized list of candidates from 'others'
            # Preference:
            #  - priority 0: idle or moving_to_field (to other targets) -- easier to reassign
            #  - priority 1: protecting other fields (less preferred to reassign)
            prioritized = []
            for d in others:
                state = getattr(d, "state", "")
                target_id = getattr(d, "target_id", None)
                if state in ("idle", "moving_to_field"):
                    priority = 0
                else:
                    # state == "protecting" but target_id != target_field.id
                    priority = 1
                dist = distance_to_field_center(d, target_field)
                prioritized.append((priority, dist, d))
            # sort by priority then distance
            prioritized.sort(key=lambda x: (x[0], x[1]))
            # select up to 'needed' drones
            for _, _, d in prioritized[:needed]:
                selected_set.add(d)

        # Now assign groups: selected_set -> protecting target_field, others -> idle
        for d in drones:
            if d in selected_set:
                environment.assign_group(d, use_protect_group)
            else:
                # assign idle (only if present in group_ids)
                if idle_group in group_ids:
                    environment.assign_group(d, idle_group)
                else:
                    # fallback: if idle not present, try any protecting group for a field with threat >0 (rare)
                    # choose the target_group if available, else first group_id.
                    fallback = target_group if target_group in group_ids else (group_ids[0] if group_ids else idle_group)
                    environment.assign_group(d, fallback)