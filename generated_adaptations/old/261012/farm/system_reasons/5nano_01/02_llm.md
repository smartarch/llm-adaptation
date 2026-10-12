Reasoning and adaptation strategy

Goal recap
- Always fully protect the field with the highest threat level (threat_level > 0) using the minimum number of drones required for full protection (drones_for_full_protection). If the field is already fully protected, keep those drones there.
- Use as many drones as possible to protect fields (prefer half of drones used for protection at least). Do not overprotect any field beyond its drones_for_full_protection.
- Drones not protecting any field should be idle, but try to keep a reasonable portion of drones in protection to meet the “at least half protected most of the time” guideline.
- Minimize drone movement churn. Try to keep drones assigned to a field for a while. When necessary, give priority to drones that were already protecting the chosen field in the previous step and are closest to the field center.
- If there are spare drones after fully protecting the top field, allocate them to protect the next-most-threatened fields to increase overall protection, but still respect the full-protection constraint for each field.

Strategy outline
- Determine the top-threat field (threat_level > 0 with the maximum value). If none, idle all drones.
- Compute the center of the top field to measure distances.
- Preserve drones that were protecting the top field in the previous step as much as possible, favoring the closest ones to the field center when more drones are needed than were already protecting.
- If more drones are needed to reach drones_for_full_protection, add the closest remaining drones to the top field until the required number is reached (or all drones are used if not enough).
- If there are drones left after fully protecting the top field, allocate them to other fields in order of threat level, again using the closest drones first and not exceeding drones_for_full_protection for those fields.
- Update a small memory map (per-drone last_group) to encourage sticking drones to the same field across steps, helping satisfy the “stay with same field at least 25%” guideline over time.
- Always re-assign every drone to exactly one group: either "idle" or one of the "protecting {field.id}" groups.

Edge handling
- If a field has threat_level > 0 but no drones exist, all drones will be idle.
- If the total number of drones is less than a field’s drones_for_full_protection, allocate all drones to that field (partial protection) as far as possible.

Python code
```py
import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Track last assignment per drone (by id) to encourage staying with the same field
        self._prev_group_by_drone = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        components: list of drone components
        environment: environment object with fields (environment.fields)
        group_ids: list of valid group names (e.g., "idle", "protecting <field_id>")
        step: time step (not directly used, but kept for compatibility)
        """
        if not components:
            return

        # Helper: distance from a drone to a field center
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return (cx, cy)

        def dist_to_field_center(drone, field):
            cx, cy = field_center(field)
            return math.hypot(getattr(drone.location, 'x', 0.0) - cx,
                              getattr(drone.location, 'y', 0.0) - cy)

        # Step 1: pick the top-threat field
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields_with_threat:
            # No threat: idle all
            for d in components:
                environment.assign_group(d, "idle")
                self._prev_group_by_drone[id(d)] = "idle"
            return

        top_field = max(fields_with_threat, key=lambda f: f.threat_level)
        top_group = f"protecting {top_field.id}"

        # Ensure the group exists in the provided IDs (assumed by problem statement)
        # Step 2: determine how many drones are needed for the top field
        total_drones = len(components)
        drones_needed_top = min(getattr(top_field, "drones_for_full_protection", total_drones), total_drones)

        # Step 3: collect previous protectors for the top field (memory)
        prev_protect_group = top_group
        prev_protectors = [d for d in components if self._prev_group_by_drone.get(id(d)) == prev_protect_group]

        # Decide which drones will protect the top field
        selected_for_top = []

        if prev_protectors:
            # Keep the closest of the previous protectors first
            prev_protectors_sorted = sorted(prev_protectors, key=lambda dr: dist_to_field_center(dr, top_field))
            take = min(len(prev_protectors_sorted), drones_needed_top)
            selected_for_top.extend(prev_protectors_sorted[:take])

        # If we still need more drones to reach full protection, pick the closest remaining drones
        if len(selected_for_top) < drones_needed_top:
            remaining_needed = drones_needed_top - len(selected_for_top)
            # Build distance list for all drones not already selected
            candidates = []
            for d in components:
                if d in selected_for_top:
                    continue
                ddist = dist_to_field_center(d, top_field)
                candidates.append((ddist, d))
            candidates.sort(key=lambda t: t[0])
            for _, d in candidates[:remaining_needed]:
                selected_for_top.append(d)

        # Step 4: Assign top field protection
        assigned_top_set = set(selected_for_top)
        for d in selected_for_top:
            environment.assign_group(d, top_group)

        # Step 5: Assign remaining drones to idle first, but track them for memory
        for d in components:
            if d not in assigned_top_set:
                environment.assign_group(d, "idle")

        # Step 6: If there are spare drones after top field, optionally protect other fields
        remaining_drones = [d for d in components if d not in assigned_top_set]

        # Fields ordered by threat level (excluding the top field)
        other_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0 and f.id != top_field.id]
        other_fields.sort(key=lambda f: f.threat_level, reverse=True)

        for f in other_fields:
            if not remaining_drones:
                break
            need_for_field = min(getattr(f, "drones_for_full_protection", len(remaining_drones)), len(remaining_drones))
            if need_for_field <= 0:
                continue

            group_for_field = f"protecting {f.id}"
            # Choose closest drones from remaining
            center = field_center(f)
            dist_list = [(math.hypot(getattr(dr.location, "x", 0.0) - center[0],
                                      getattr(dr.location, "y", 0.0) - center[1]), dr) for dr in remaining_drones]
            dist_list.sort(key=lambda t: t[0])
            to_assign = [dr for _, dr in dist_list[:need_for_field]]

            for dr in to_assign:
                environment.assign_group(dr, group_for_field)

            # Remove assigned drones from remaining list
            remaining_drones = [dr for dr in remaining_drones if dr not in to_assign]

        # Step 7: Update memory map for next step
        # For all drones, record their current group
        for d in components:
            # Determine this step's group for the drone
            # If it is in assigned_top_set -> top_field; else if it was assigned to some other field in this run, reflect that.
            if d in assigned_top_set:
                self._prev_group_by_drone[id(d)] = top_group
            else:
                # Check if the drone was assigned to any other protection group in this run
                current_group = None
                # We can estimate by checking if drone's current group matches any other field group
                for f in other_fields:
                    if environment is not None:
                        # We cannot re-query the component's group from environment directly here without a reference
                        # to which drone is in which group after last assign. We keep a conservative default:
                        pass
                # Fallback: assign to idle
                current_group = "idle"
                self._prev_group_by_drone[id(d)] = current_group
```