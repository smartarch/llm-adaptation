Reasoning and high-level strategy

Goals and constraints
- Always fully protect the single most threatened field, using the closest drones.
- Avoid overprotection (don't assign more drones than the field's drones_for_full_protection).
- Keep drones stable (avoid moving drones unnecessarily) — prefer to keep drones that are already protecting a field there.
- Use at least half the fleet for protection most of the time if possible.
- Prefer fully protecting fewer fields rather than partially protecting many.

Key ideas used in the strategy
1. Maintain a small internal state across adaptation calls:
   - last assigned group per drone and a consecutive-step streak counter per drone. This helps prefer keeping drones on the same tasks and avoid thrashing.
2. For the most threatened field:
   - Select up to drones_for_full_protection drones, preferring (in this order):
     a) drones that are already assigned to that field (protecting / moving_to_field),
     b) drones closest to the field (distance to field center),
     c) among equally close candidates prefer drones with shorter streaks (they're cheaper to move).
   - Assign exactly the number needed (no overprotection).
3. After protecting the top field:
   - Ensure at least half of the drones are assigned to protection if possible. If protecting the top field already uses half or more, we stop (remaining drones go idle).
   - Otherwise, try to fully protect the next-most-threatened fields using the remaining drones (again preferring those already assigned there and closest drones), until we either reach the half-fleet protection target or run out of full-field opportunities.
   - If we still haven't reached half the fleet, assign the remaining needed drones to the next highest-threat field (partial protection) to reach the target.
   - Any drones not needed are assigned 'idle'.
4. Stability:
   - When selecting which drones to move, prefer moving drones with low streaks (those that have not been on the same assignment for long). This tends to keep at least half the drones on the same field for longer periods.

This approach satisfies:
- Most-threatened field is always fully protected and by the closest drones.
- Avoids overprotection (exact number of protecting drones equals drones_for_full_protection).
- Attempts to avoid too many idle drones (aims for at least half used in protection).
- Prefers to keep drones in the same roles (tracks and uses streaks).

Implementation notes
- The code stores per-drone last assignment and streak in self.last_group and self.streaks. It uses either a drone's 'id' attribute (if present) or Python's id(component) as a stable key.
- All drones are explicitly assigned to groups every call as required.
- The group strings used are exactly "idle" or "protecting {field.id}" per the instructions.
- The method uses only observation attributes and environment.assign_group to set groups.

Code

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # per-drone persistent state: last assigned group and how many consecutive steps it stayed that group
        self.last_group = {}   # key -> group_id
        self.streaks = {}      # key -> consecutive step count
        self.last_step = None

    def _drone_key(self, component):
        # Prefer explicit id if present, otherwise Python id
        cid = getattr(component, 'id', None)
        return cid if cid is not None else id(component)

    def _distance_sq_to_field_center(self, component, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        dx = component.location.x - cx
        dy = component.location.y - cy
        return dx*dx + dy*dy

    def assign_drones(self, components, environment, group_ids, step: int):
        # Build list of fields with positive threat, sorted descending by threat
        fields = [f for f in environment.fields if f.threat_level > 0]
        fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Prepare drone metadata
        drone_list = []
        for comp in components:
            key = self._drone_key(comp)
            prev_group = self.last_group.get(key)
            prev_streak = self.streaks.get(key, 0)
            drone_list.append({
                'comp': comp,
                'key': key,
                'state': getattr(comp, 'state', None),
                'target_id': getattr(comp, 'target_id', None),
                'loc_x': getattr(comp, 'location').x,
                'loc_y': getattr(comp, 'location').y,
                'prev_group': prev_group,
                'prev_streak': prev_streak
            })

        total_drones = len(drone_list)
        assignments = {}  # key -> group_name

        # If no fields to protect, assign all drones to 'idle'
        if not fields:
            for d in drone_list:
                assignments[d['key']] = 'idle'
            # apply assignments and update internal state
            for d in drone_list:
                comp = d['comp']
                g = assignments[d['key']]
                environment.assign_group(comp, g)
                key = d['key']
                if self.last_group.get(key) == g:
                    self.streaks[key] = self.streaks.get(key, 0) + 1
                else:
                    self.streaks[key] = 1
                self.last_group[key] = g
            self.last_step = step
            return

        # Helper to pick best drones for a particular field, given candidate pool and needed count.
        def pick_drones_for_field(field, candidates, need):
            # candidates: list of drone dicts
            # Preference order:
            # 1) drones already targeting/assigned to this field (state in protecting/moving_to_field and target_id==field.id)
            # 2) then closest drones
            # tie-breaker: prefer drones with smaller prev_streak (less stable) to move them
            cur_assigned = []
            others = []
            for d in candidates:
                is_assigned = (d['state'] in ('protecting', 'moving_to_field') and d['target_id'] == field.id)
                if is_assigned:
                    cur_assigned.append(d)
                else:
                    others.append(d)
            # sort current assigned by distance ascending (and smaller prev_streak last? we want keep stable ones, so prefer larger prev_streak)
            cur_assigned.sort(key=lambda d: (self._distance_sq_to_field_center(d['comp'], field), -d['prev_streak']))
            # sort others by distance ascending, prefer smaller prev_streak to move them
            others.sort(key=lambda d: (self._distance_sq_to_field_center(d['comp'], field), d['prev_streak']))
            chosen = []
            for d in cur_assigned:
                if len(chosen) >= need:
                    break
                chosen.append(d)
            for d in others:
                if len(chosen) >= need:
                    break
                chosen.append(d)
            return chosen

        # Start with the most threatened field: fully protect it with closest drones (preferring those already there)
        primary = fields[0]
        need_primary = int(primary.drones_for_full_protection)
        # Build candidates: all drones not yet assigned
        unassigned = list(drone_list)

        selected_primary = pick_drones_for_field(primary, unassigned, need_primary)
        # Assign those selected to primary protecting
        protecting_group_name = f"protecting {primary.id}"
        for d in selected_primary:
            assignments[d['key']] = protecting_group_name
        # Remove them from unassigned
        selected_keys = set(d['key'] for d in selected_primary)
        unassigned = [d for d in unassigned if d['key'] not in selected_keys]

        # Ensure we didn't overprotect (we selected at most need_primary)
        protecting_count = len(selected_primary)

        # Now ensure at least half of drones are protecting if possible
        desired_protectors = max(math.ceil(total_drones / 2.0), protecting_count)
        remaining_needed = desired_protectors - protecting_count

        # Try to fully protect next fields (respecting "prefer fully protecting fewer fields")
        for field in fields[1:]:
            if remaining_needed <= 0:
                break
            need = int(field.drones_for_full_protection)
            # Can we fully protect this field with available unassigned drones?
            if len(unassigned) >= need:
                chosen = pick_drones_for_field(field, unassigned, need)
                # assign chosen to this field
                group_name = f"protecting {field.id}"
                for d in chosen:
                    assignments[d['key']] = group_name
                chosen_keys = set(d['key'] for d in chosen)
                unassigned = [d for d in unassigned if d['key'] not in chosen_keys]
                protecting_count += len(chosen)
                remaining_needed = desired_protectors - protecting_count
            else:
                # Not enough to fully protect. If we still need some to reach half, assign as many as needed to this field (partial),
                # otherwise skip (we prefer not to partial-protect if not required).
                if remaining_needed > 0 and len(unassigned) > 0:
                    to_take = min(len(unassigned), remaining_needed)
                    chosen = pick_drones_for_field(field, unassigned, to_take)
                    group_name = f"protecting {field.id}"
                    for d in chosen:
                        assignments[d['key']] = group_name
                    chosen_keys = set(d['key'] for d in chosen)
                    unassigned = [d for d in unassigned if d['key'] not in chosen_keys]
                    protecting_count += len(chosen)
                    remaining_needed = desired_protectors - protecting_count
                # else skip partial
        # If after going through fields we still haven't reached desired_protectors, and there are unassigned drones,
        # assign them to the highest-threat field (secondary) as needed (this is a last resort to fulfill the "half protection" requirement).
        if remaining_needed > 0 and unassigned:
            # choose the next field (if exists) else assign to primary (but not exceeding drones_for_full_protection)
            second_field = fields[1] if len(fields) > 1 else primary
            # calculate how many we can assign to second_field such that we don't exceed its drones_for_full_protection
            already_assigned_to_second = sum(1 for k, g in assignments.items() if g == f"protecting {second_field.id}")
            can_assign_to_second = int(second_field.drones_for_full_protection) - already_assigned_to_second
            to_assign = min(remaining_needed, len(unassigned), max(0, can_assign_to_second))
            if to_assign > 0:
                chosen = pick_drones_for_field(second_field, unassigned, to_assign)
                group_name = f"protecting {second_field.id}"
                for d in chosen:
                    assignments[d['key']] = group_name
                chosen_keys = set(d['key'] for d in chosen)
                unassigned = [d for d in unassigned if d['key'] not in chosen_keys]
                protecting_count += len(chosen)
                remaining_needed = desired_protectors - protecting_count

        # Any drones left unassigned -> idle
        for d in unassigned:
            assignments[d['key']] = 'idle'

        # Now apply assignments to components and update internal state (streaks and last_group)
        for d in drone_list:
            comp = d['comp']
            key = d['key']
            group = assignments.get(key, 'idle')
            # Ensure group name is valid (should be, but guard)
            # group ids are provided; assume our constructed groups are valid per spec.
            environment.assign_group(comp, group)
            # Update streaks: if same as last_group increment, otherwise reset to 1
            if self.last_group.get(key) == group:
                self.streaks[key] = self.streaks.get(key, 0) + 1
            else:
                self.streaks[key] = 1
            self.last_group[key] = group

        # Update last_step
        self.last_step = step
```