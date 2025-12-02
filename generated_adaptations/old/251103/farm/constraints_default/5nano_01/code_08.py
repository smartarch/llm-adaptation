"""
Strategy reasoning (embedded as module docstring):
- Goal: allocate drones to protect farm fields by creating protection groups.
- Key rules:
  - Always fully protect the most threatened field (highest threat_level among fields with threat > 0) using drones equal to that field's drones_for_full_protection.
  - If that field already has full protection, keep those drones in place and do not move them unnecessarily.
  - Use idle drones first to fill protection needs, to minimize changes to drones currently protecting other fields.
  - After attempting to fully protect the top field, we can allocate additional idle drones to other threatened fields (in descending threat order) as long as we stay within the rule of using idle drones first and never disturb current protectors unnecessarily.
  - For each assignment, use the exact group names:
    - "idle" for drones not protecting any field
    - "protecting {field.id}" for drones protecting a given field
- Implementation notes:
  - We determine the best field as the top-threat field; if there are ties, we prefer the field with fewer current protectors to minimize moves.
  - We only promote idle drones to protection groups, preserving any drones already protecting a field unless they need to switch to a higher-priority field to achieve full protection.
  - We always assign all drones to a group (either a protection group or "idle") to satisfy the assignment contract.
"""

from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: squared distance from a drone location to a field center
        def distance2(loc, center):
            if loc is None:
                return float('inf')
            x = getattr(loc, 'x', None)
            y = getattr(loc, 'y', None)
            if x is None or y is None:
                return float('inf')
            dx = x - center[0]
            dy = y - center[1]
            return dx * dx + dy * dy

        # Gather threatened fields (threat_level > 0)
        fields = getattr(environment, 'fields', [])
        threatened_fields = [f for f in fields if getattr(f, 'threat_level', 0) > 0]

        # If nothing is threatened, idle all drones
        if not threatened_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Determine the maximum threat level and candidate top fields
        max_threat = max(getattr(f, 'threat_level', 0) for f in threatened_fields)
        top_fields = [f for f in threatened_fields if getattr(f, 'threat_level', 0) == max_threat]

        # Pick the best field: fewest current protectors among the top-threat fields
        current_counts = {f.id: 0 for f in top_fields}
        for c in components:
            tid = getattr(c, 'target_id', None)
            if tid in current_counts:
                current_counts[tid] += 1
        best_field = min(top_fields, key=lambda f: current_counts.get(f.id, 0))

        # We'll attempt to fully protect the best_field first
        field = best_field
        protect_group = f"protecting {field.id}"
        required = int(getattr(field, 'drones_for_full_protection', 0))

        # Current number of drones protecting this field (count by target_id)
        current_for_field = int(current_counts.get(field.id, 0))

        # Drones currently protecting this field
        currently_protecting = [c for c in components if getattr(c, 'target_id', None) == field.id]

        # Center of the field
        center = ((getattr(field, 'left') + getattr(field, 'right')) / 2.0,
                  (getattr(field, 'top') + getattr(field, 'bottom')) / 2.0)

        # How many more drones needed to fully protect this field
        needed = max(0, required - current_for_field)

        # Idle drones available for promotion
        idle_drones = [c for c in components if getattr(c, 'state', None) == 'idle']
        idle_sorted = sorted(idle_drones, key=lambda c: distance2(getattr(c, 'location', None), center))

        to_promote = idle_sorted[:min(needed, len(idle_sorted))]

        # Promote selected drones to the protection group
        for c in to_promote:
            environment.assign_group(c, protect_group)

        # Ensure currently protecting drones for this field stay in the protection group
        for c in currently_protecting:
            environment.assign_group(c, protect_group)

        # After filling the top field, try to allocate any remaining idle drones to other threatened fields
        # in descending threat order, without disturbing already-protected drones.
        remaining_idle = idle_sorted[len(to_promote):]  # those not promoted to the top field
        # Build a list of other threatened fields excluding the top one
        other_fields = [f for f in top_fields if f.id != field.id] + \
                       [f for f in threatened_fields if f not in top_fields and getattr(f, 'threat_level', 0) > 0]
        # Sort other fields by threat (desc), then by smallest existing protectors to minimize moves
        other_fields = sorted(other_fields, key=lambda f: (-getattr(f, 'threat_level', 0), int(getattr(f, 'drones_for_full_protection', 0))))

        allocated_any = set(to_promote)
        allocated_any.update(currently_protecting)

        for f in other_fields:
            group = f"protecting {f.id}"
            # Current protectors for this field
            current_for_f = sum(1 for c in components if getattr(c, 'target_id', None) == f.id)

            required_f = int(getattr(f, 'drones_for_full_protection', 0))
            need_f = max(0, required_f - current_for_f)

            if need_f <= 0:
                continue

            # Use remaining idle drones if available
            if not remaining_idle:
                break

            # Recompute distance to this field's center
            center_f = ((getattr(f, 'left') + getattr(f, 'right')) / 2.0,
                        (getattr(f, 'top') + getattr(f, 'bottom')) / 2.0)
            # Re-sort remaining idle by proximity to this field
            remaining_idle = sorted(remaining_idle, key=lambda c: distance2(getattr(c, 'location', None), center_f))
            take = min(need_f, len(remaining_idle))
            for i in range(take):
                c = remaining_idle[i]
                environment.assign_group(c, group)
                allocated_any.add(c)

            # Remove chosen from remaining_idle
            remaining_idle = remaining_idle[take:]

        # Finally, ensure every drone has a group to satisfy explicit reassignment:
        # Drones that were not allocated to a protecting group in this pass become idle.
        allocated = set(to_promote)
        allocated.update(currently_protecting)
        # Also include any drones moved to other protect groups in the "other_fields" loop
        for c in components:
            if c in allocated:
                continue
            # If c is protecting some field in the current environment and that field is still protected by this strategy,
            # we leave it as is (no explicit reassignment required here). Otherwise, make it idle for cleanliness.
            current_tid = getattr(c, 'target_id', None)
            if current_tid is None:
                environment.assign_group(c, "idle")
            else:
                # If the targeted field is not in the list of fields we considered, still assign to idle to keep things explicit
                environment.assign_group(c, "idle")