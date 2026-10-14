from generated_adaptations.base_classes.farm import FarmAdaptation
import math


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._prev_assignments = {}  # component_id -> group_name
        self._step_count = 0

    def assign_drones(self, components, environment, group_ids, step: int):
        self._step_count = step
        num_drones = len(components)

        # Build a lookup for drone IDs
        drone_ids = {id(d): d for d in components}

        # Get all threatened fields sorted by weighted threat level (aggressive weighting)
        threatened_fields = sorted(
            [f for f in environment.fields if f.threat_level > 0],
            key=lambda f: f.threat_level ** 1.5,
            reverse=True
        )

        # If no threats, all drones idle
        if not threatened_fields:
            for drone in components:
                environment.assign_group(drone, "idle")
            self._prev_assignments = {id(d): "idle" for d in components}
            return

        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return (cx, cy)

        def distance_to_field(drone, field):
            cx, cy = field_center(field)
            return math.sqrt((drone.location.x - cx) ** 2 + (drone.location.y - cy) ** 2)

        def group_for_field(field_id):
            return f"protecting {field_id}"

        # Determine current valid field group ids
        valid_field_groups = {group_for_field(f.id) for f in environment.fields if f.threat_level > 0}

        # Classify drones into categories for smart assignment
        # Priority 1: Already protecting a still-threatened field (highest stickiness)
        # Priority 2: Moving to a still-threatened field
        # Priority 3: Idle drones
        # Priority 4: Drones targeting a now-unthreatened field (free agents)

        # First pass: identify drones that should STAY on current assignment
        stay_assignments = {}  # drone -> group_name
        free_drones = []  # drones available for reassignment

        for drone in components:
            prev_group = self._prev_assignments.get(id(drone))

            if drone.state == "protecting" and drone.target_id:
                target_field = next((f for f in environment.fields if f.id == drone.target_id), None)
                if target_field and target_field.threat_level > 0:
                    # Drone is protecting a still-threatened field - very sticky
                    # Only pull if we absolutely need them for the most threatened field
                    stay_assignments[drone] = group_for_field(drone.target_id)
                    continue

            if drone.state == "moving_to_field" and drone.target_id:
                target_field = next((f for f in environment.fields if f.id == drone.target_id), None)
                if target_field and target_field.threat_level > 0:
                    # In transit to a still-threatened field - let it finish
                    stay_assignments[drone] = group_for_field(drone.target_id)
                    continue

            # Drone is idle or targeting an unthreatened field - available for reassignment
            free_drones.append(drone)

        # Count how many are staying per field group
        field_assigned_count = {}
        for drone, group in stay_assignments.items():
            field_assigned_count[group] = field_assigned_count.get(group, 0) + 1

        # Build field lookup
        field_by_id = {f.id: f for f in environment.fields}

        # === Step 1: Ensure most threatened field is FULLY protected ===
        most_threatened = threatened_fields[0]
        mt_group = group_for_field(most_threatened.id)
        needed_for_mt = most_threatened.drones_for_full_protection
        currently_on_mt = field_assigned_count.get(mt_group, 0)
        deficit = needed_for_mt - currently_on_mt

        if deficit > 0 and free_drones:
            # Select closest free drones for the most threatened field
            free_sorted = sorted(free_drones, key=lambda d: distance_to_field(d, most_threatened))
            to_assign = free_sorted[:min(deficit, len(free_sorted))]
            for d in to_assign:
                stay_assignments[d] = mt_group
                free_drones.remove(d)
            field_assigned_count[mt_group] = needed_for_mt
            # Recalculate deficit
            deficit = 0

        # === Step 2: Ensure NO overprotection - release excess from all fields ===
        for field in environment.fields:
            if field.threat_level <= 0:
                continue
            fg = group_for_field(field.id)
            assigned = field_assigned_count.get(fg, 0)
            needed = field.drones_for_full_protection
            if assigned > needed:
                # Release excess drones from this field
                excess = assigned - needed
                drones_on_this = [d for d, g in stay_assignments.items() if g == fg]
                # Sort by distance - keep closest ones
                drones_on_this.sort(key=lambda d: distance_to_field(d, field))
                to_release = drones_on_this[needed:]  # Release the farthest
                for d in to_release:
                    del stay_assignments[d]
                    free_drones.append(d)
                    field_assigned_count[fg] -= 1

        # === Step 3: Greedily fully protect secondary threatened fields ===
        total_protecting = len(stay_assignments)
        for field in threatened_fields[1:]:
            if not free_drones:
                break
            fg = group_for_field(field.id)
            already_assigned = field_assigned_count.get(fg, 0)
            needed = field.drones_for_full_protection
            still_need = needed - already_assigned

            if still_need <= 0:
                continue  # Already fully protected
            if len(free_drones) < still_need:
                break  # Can't fully protect this field; skip (prefer full over partial)

            free_sorted = sorted(free_drones, key=lambda d: distance_to_field(d, field))
            to_assign = free_sorted[:still_need]
            for d in to_assign:
                stay_assignments[d] = fg
                free_drones.remove(d)
            field_assigned_count[fg] = needed
            total_protecting += len(to_assign)

        # === Step 4: Reduce idle count - assign spare drones to partially protect high-threat fields ===
        half_threshold = num_drones / 2.0
        total_protecting = len(stay_assignments)

        if total_protecting < half_threshold and free_drones:
            # Only assign partial protection to fields with threat > 0.25
            # Distribute one at a time, avoiding overprotection
            partial_fields = sorted(
                [f for f in threatened_fields if f.threat_level > 0.25],
                key=lambda f: f.threat_level,
                reverse=True
            )

            for field in partial_fields:
                if not free_drones:
                    break
                if len(stay_assignments) >= half_threshold:
                    break
                fg = group_for_field(field.id)
                currently = field_assigned_count.get(fg, 0)
                if currently >= field.drones_for_full_protection:
                    continue  # Don't overprotect
                # Assign one drone (partial protection, but better than idle)
                d = free_drones[0]
                # Prefer closest free drone
                free_drones.sort(key=lambda dd: distance_to_field(dd, field))
                d = free_drones[0]
                stay_assignments[d] = fg
                free_drones.remove(d)
                field_assigned_count[fg] = currently + 1

        # === Step 5: Remaining drones go idle ===
        final_assignments = {}
        for drone, group in stay_assignments.items():
            final_assignments[drone] = group
        for drone in free_drones:
            final_assignments[drone] = "idle"

        # === Apply assignments ===
        for drone in components:
            group = final_assignments.get(drone, "idle")
            # Validate group exists in group_ids
            if group not in group_ids:
                group = "idle"
            environment.assign_group(drone, group)

        # === Save for next step's stickiness ===
        self._prev_assignments = {id(d): final_assignments.get(d, "idle") for d in components}