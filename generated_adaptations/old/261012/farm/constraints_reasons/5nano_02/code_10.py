from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Remember previous step's assignments to help persistence
        self.prev_assignments = {}

    def _distance_to_field_center(self, comp, field_center):
        loc = getattr(comp, 'location', None)
        if loc is None:
            return float('inf')
        return math.hypot(loc.x - field_center[0], loc.y - field_center[1])

    def _collect_candidates_for_field(self, field, field_group, components, prev_assignments, assigned_mask, limit):
        '''
        Build candidate drones for a field, preferring drones that were previously in this field's group
        or currently heading/protecting this field. Then fill with closest remaining drones.
        Returns a list of drone indices (length up to limit).
        '''
        cx = (field.left + field.right) / 2.0
        cy = (field.top  + field.bottom) / 2.0
        center = (cx, cy)

        # Distances to field center
        dists = [self._distance_to_field_center(c, center) for c in components]

        # Primary pool: drones that were previously in this field's group or currently targeting it
        primary = []
        if field_group in self.group_ids if hasattr(self, 'group_ids') else False:
            pass  # placeholder to ensure linter calm if needed

        prev_group = field_group
        for i, comp in enumerate(components):
            # Skip already assigned drones
            if i in assigned_mask:
                continue
            dist = dists[i]
            was_before = (prev_assignments.get(i, '') == prev_group)
            currently_heading = (getattr(comp, 'state', None) in ('protecting','moving_to_field') and
                                 getattr(comp, 'target_id', None) == field.id)
            if was_before or currently_heading:
                primary.append((i, dist))

        # If primary is too short, add more drones from all, but keep preference ordering
        primary.sort(key=lambda t: t[1])

        candidates = [idx for idx, _ in primary]

        if len(candidates) < limit:
            # Add closest non-assigned drones
            remaining = [(i, dists[i]) for i in range(len(components)) if i not in assigned_mask and i not in candidates]
            remaining.sort(key=lambda t: t[1])
            for i, _ in remaining:
                if len(candidates) >= limit:
                    break
                candidates.append(i)

        return candidates[:limit]

    def assign_drones(self, components, environment, group_ids, step: int):
        # Cache for reuse
        self.group_ids = group_ids

        n = len(components)
        fields = getattr(environment, 'fields', []) or []
        threat_fields = [f for f in fields if getattr(f, 'threat_level', 0) > 0]

        # If no threats, idle all drones
        if not threat_fields:
            for i, comp in enumerate(components):
                environment.assign_group(comp, 'idle')
                self.prev_assignments[i] = 'idle'
            return

        # Sort threat fields by threat level (desc)
        threat_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # First pass: fully protect as many threat fields as possible, in threat order
        assigned = ['idle'] * n
        used = [False] * n  # mark drones already assigned to a protective group

        for field in threat_fields:
            group = f"protecting {field.id}"
            if group not in group_ids:
                continue  # cannot assign to this field
            required = max(0, int(getattr(field, 'drones_for_full_protection', 0)))
            if required <= 0:
                continue

            candidates = self._collect_candidates_for_field(
                field=field,
                field_group=group,
                components=components,
                prev_assignments=self.prev_assignments,
                assigned_mask={i for i, s in enumerate(assigned) if s != 'idle'},
                limit=required
            )

            # Assign selected drones to this field
            for idx in candidates:
                if idx < 0 or idx >= n:
                    continue
                if assigned[idx] != group:
                    assigned[idx] = group
                    used[idx] = True

        # Second pass: ensure at least half the drones are protecting something
        half_target = int(math.ceil(n / 2.0))
        current_protected = sum(1 for s in assigned if s != 'idle')

        # Iterate over secondary fields (in threat order)
        for field in threat_fields:
            if current_protected >= half_target:
                break
            group = f"protecting {field.id}"
            if group not in group_ids:
                continue
            # If this field already has full protection via assigned drones, skip
            cap = max(0, int(getattr(field, 'drones_for_full_protection', 0)))
            # Count drones currently assigned to this group
            current_for_field = sum(1 for s in assigned if s == group)
            if current_for_field >= cap:
                continue

            need = cap - current_for_field
            # Build pool: drones not currently in this group
            pool = []
            for i in range(n):
                if assigned[i] != group:
                    # Dist to field
                    fx = (field.left + field.right) / 2.0
                    fy = (field.top  + field.bottom) / 2.0
                    loc = getattr(components[i], 'location', None)
                    d = float('inf')
                    if loc is not None:
                        d = math.hypot(loc.x - fx, loc.y - fy)
                    pool.append((i, d))
            pool.sort(key=lambda t: t[1])

            # First try to take from drones previously protecting this field
            taken = []
            for i, _ in pool:
                if len(taken) >= need:
                    break
                if self.prev_assignments.get(i, '') == group:
                    taken.append(i)

            for i in pool:
                if len(taken) >= need:
                    break
                idx = i[0]
                if idx not in taken and assigned[idx] != group:
                    taken.append(idx)

            for idx in taken:
                if 0 <= idx < n and assigned[idx] != group:
                    assigned[idx] = group
                    current_protected += 1
                    need -= 1
                    if current_protected >= half_target:
                        break

        # Any remaining unassigned drones go idle
        for i in range(n):
            if assigned[i] not in group_ids:
                assigned[i] = 'idle'

        # Apply assignments and persist them
        for i, comp in enumerate(components):
            grp = assigned[i]
            if grp not in group_ids:
                grp = 'idle'
            environment.assign_group(comp, grp)
            self.prev_assignments[i] = grp