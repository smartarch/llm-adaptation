from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Remember previous step's assignments to preserve persistence
        # Key: drone index, value: group_id string
        self.prev_assignments = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Number of drones
        n_drones = len(components)

        # Gather threat-enabled fields
        fields = getattr(environment, 'fields', []) or []
        threat_fields = [f for f in fields if getattr(f, 'threat_level', 0) > 0]

        # If there are no threats, idle all drones
        if not threat_fields:
            for i, comp in enumerate(components):
                group = 'idle'
                if group not in group_ids:
                    group = 'idle'
                environment.assign_group(comp, group)
                self.prev_assignments[i] = group
            return

        # Sort threat fields by threat level (desc)
        threat_fields.sort(key=lambda f: f.threat_level, reverse=True)
        top_field = threat_fields[0]
        top_group = f"protecting {top_field.id}"
        if top_group not in group_ids:
            # Fallback to idle if somehow the group isn't valid
            top_group = 'idle'

        # How many drones are needed for full protection of the top field
        required = max(0, int(top_field.drones_for_full_protection))

        # Field center for distance calculations
        cx = (top_field.left + top_field.right) / 2.0
        cy = (top_field.top + top_field.bottom) / 2.0

        def dist_to_field(idx, field_center):
            loc = getattr(components[idx], 'location', None)
            if loc is None:
                return float('inf')
            return math.hypot(loc.x - field_center[0], loc.y - field_center[1])

        # Determine which drones were protecting the top field in the previous step
        prev_top_group = f"protecting {top_field.id}"
        keep_candidates = []
        for i, comp in enumerate(components):
            if self.prev_assignments.get(i) == prev_top_group:
                d = dist_to_field(i, (cx, cy))
                keep_candidates.append((i, d))

        # Prefer keeping the closest previous protectors
        keep_candidates.sort(key=lambda t: t[1])
        to_protect = []
        max_keep = min(required, n_drones)
        for idx, _ in keep_candidates:
            if len(to_protect) >= max_keep:
                break
            to_protect.append(idx)

        # If we still need more to reach full protection, pick closest remaining drones
        if len(to_protect) < max_keep:
            remaining = [(i, dist_to_field(i, (cx, cy))) for i in range(n_drones) if i not in to_protect]
            remaining.sort(key=lambda t: t[1])
            for i, _ in remaining:
                if len(to_protect) >= max_keep:
                    break
                to_protect.append(i)

        # Build final assignments per drone
        assigned_group = {}

        # Assign top field protection
        for idx in to_protect:
            assigned_group[idx] = top_group

        # Now ensure we use at least half the drones for protection.
        half_target = int(math.ceil(n_drones / 2.0))
        current_protected = len(to_protect)

        # If we haven't reached half the drones, try to protect other fields (secondaries)
        if current_protected < half_target:
            # Consider other threat fields (excluding the top one)
            other_fields = threat_fields[1:]
            # Indices not yet assigned to a protection group
            unassigned = [i for i in range(n_drones) if i not in assigned_group]

            for f in other_fields:
                if current_protected >= half_target:
                    break
                group_name = f"protecting {f.id}"
                if group_name not in group_ids:
                    continue

                fx = (f.left + f.right) / 2.0
                fy = (f.top + f.bottom) / 2.0
                # sort remaining by distance to this field
                pool = [(i, math.hypot(components[i].location.x - fx, components[i].location.y - fy)) for i in unassigned]
                pool.sort(key=lambda t: t[1])

                max_field = max(0, int(f.drones_for_full_protection))
                slots = min(max_field, len(pool))

                for j in range(slots):
                    idx = pool[j][0]
                    assigned_group[idx] = group_name
                    unassigned.remove(idx)
                    current_protected += 1
                    if current_protected >= half_target:
                        break

                if current_protected >= half_target:
                    break

        # Any drones not assigned yet go idle
        for i in range(n_drones):
            if i not in assigned_group:
                assigned_group[i] = 'idle'

        # Apply assignments and remember them for persistence
        for i, comp in enumerate(components):
            group = assigned_group.get(i, 'idle')
            if group not in group_ids:
                group = 'idle'
            environment.assign_group(comp, group)
            self.prev_assignments[i] = group