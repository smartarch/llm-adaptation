Reasoning and strategy improvements

What went wrong before
- The previous approach greedily protected the single most threatened field and then tried to reach a "half of drones protecting" target by protecting additional fields in a simple order. That sometimes left many drones idle or allocated suboptimally across fields, and it didn't select which fields to fully protect in a way that maximizes threat reduction per drone.

Key improvements in this version
1. Select which fields to fully protect using a density (threat per required drone) greedy strategy:
   - Always include the single most threatened field (functional requirement).
   - Then pick additional fields in descending order of (threat_level / drones_for_full_protection) until we run out of drone capacity.
   - This prefers fields that give the most threat reduction per drone and thus reduces expected damage for a fixed drone budget.
2. Respect current assignments and stability:
   - Keep drones already assigned to a chosen field when possible.
   - When choosing which drones to move, prefer drones with low stability streaks (they've been moved recently) to reduce thrashing and satisfy the "keep drones stable" requirement.
   - For the primary (most threatened) field, prioritize the physically closest drones (this satisfies the explicit requirement that "drones protecting the most threatened field should be the closest ones").
3. Ensure at least half of the fleet is used for protection when feasible:
   - After selecting fully protected fields, if fewer than half the drones are protecting, we assign additional drones (possibly partially) to the next-best field(s) until the half-fleet target is reached or no more drones are available. We try to avoid partial protection unless necessary to meet the "half protecting" constraint.
4. Avoid overprotection:
   - Never assign more drones to a field than its drones_for_full_protection.
5. Persistent per-drone streak bookkeeping:
   - Track last assigned group and consecutive-step streaks. We prefer moving drones with small streaks to preserve stability for those with long streaks.

Overall effect
- The combination of threat-per-drone selection and distance-aware assignment (especially for the top field) aims to reduce damage by maximizing protected threat per drone while honoring the functional constraints.

Implementation follows: a class SmartFarmAdaptation derived from FarmAdaptation. The code stores per-drone last group and streaks, chooses fields to fully protect by density, allocates drones accordingly, fills to the half-fleet requirement if needed, and applies assignments via environment.assign_group(component, group_id).

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # persistent per-drone state to prefer stability
        self.last_group = {}   # key -> last group_id
        self.streaks = {}      # key -> consecutive steps in same group

    def _drone_key(self, component):
        cid = getattr(component, 'id', None)
        return cid if cid is not None else id(component)

    def _field_center(self, field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _dist_sq(self, comp, field):
        cx, cy = self._field_center(field)
        dx = comp.location.x - cx
        dy = comp.location.y - cy
        return dx*dx + dy*dy

    def assign_drones(self, components, environment, group_ids, step: int):
        # Build drone metadata
        drones = []
        for comp in components:
            key = self._drone_key(comp)
            drones.append({
                'comp': comp,
                'key': key,
                'state': getattr(comp, 'state', None),
                'target_id': getattr(comp, 'target_id', None),
                'prev_group': self.last_group.get(key),
                'prev_streak': self.streaks.get(key, 0)
            })

        total_drones = len(drones)
        if total_drones == 0:
            return

        # Build fields list with positive threat
        fields = [f for f in environment.fields if f.threat_level > 0]
        if not fields:
            # Nothing to protect -> idle all
            for d in drones:
                environment.assign_group(d['comp'], 'idle')
                key = d['key']
                if self.last_group.get(key) == 'idle':
                    self.streaks[key] = self.streaks.get(key, 0) + 1
                else:
                    self.streaks[key] = 1
                self.last_group[key] = 'idle'
            return

        # Always ensure primary (most-threat) is first
        fields.sort(key=lambda f: f.threat_level, reverse=True)
        primary = fields[0]

        # Count currently assigned drones per field (based on observed state and target_id)
        assigned_counts = {}
        for f in fields:
            assigned_counts[f.id] = 0
        for d in drones:
            if d['state'] in ('protecting', 'moving_to_field') and d['target_id'] in assigned_counts:
                assigned_counts[d['target_id']] += 1

        # Selection of fields to fully protect:
        # Always include primary. Then greedily include fields by density = threat_level / drones_for_full_protection
        capacity = total_drones  # total drone capacity (we'll reserve full counts for chosen fields)
        selected_fields = []
        # Handle case where primary requires more drones than available: we will still include primary,
        # but the allocation step will assign as many as possible (functional requirement: keep it fully protected if possible).
        selected_fields.append(primary)
        cap_after_primary = capacity - min(primary.drones_for_full_protection, capacity)
        capacity = capacity  # keep original capacity for planning sum check below

        # prepare list of other fields with density
        other_fields = fields[1:]
        other_fields.sort(key=lambda f: (f.threat_level / max(1, f.drones_for_full_protection)), reverse=True)

        # Greedy choose additional fields so that sum(drones_for_full_protection) <= total_drones
        sum_needed = min(primary.drones_for_full_protection, total_drones)
        for f in other_fields:
            need = int(f.drones_for_full_protection)
            if sum_needed + need <= total_drones:
                selected_fields.append(f)
                sum_needed += need

        # Now allocate drones to selected fields:
        # For primary, requirement: drones protecting it should be the closest ones -> choose closest drones for primary.
        # For other fields, prefer drones already assigned there, then closest among remaining, prefer moving low-streak drones.

        # We'll build assignments keyed by drone key
        assignments = {}

        # Helper: pick N drones for a field from a pool of available drones
        def pick_n_for_field(field, available_list, n, prefer_keep_assigned=False, primary_field=False):
            # available_list: list of drone dicts not yet assigned
            if n <= 0:
                return []
            # compute distance, whether currently assigned to that field, streak
            enriched = []
            for d in available_list:
                dist = self._dist_sq(d['comp'], field)
                is_assigned_now = (d['state'] in ('protecting', 'moving_to_field') and d['target_id'] == field.id)
                enriched.append((d, dist, is_assigned_now, d['prev_streak']))
            chosen = []
            if primary_field:
                # For primary: pick closest drones first. Tie-breaker: prefer already assigned, then prefer low streak to move
                enriched.sort(key=lambda tup: (tup[1], 0 if tup[2] else 1, tup[3]))
                for tup in enriched:
                    if len(chosen) >= n:
                        break
                    chosen.append(tup[0])
            else:
                # For non-primary: prefer those already assigned to this field (and with higher streak to preserve stability),
                # then others by distance and low streak (prefer moving low-streak ones).
                assigned_now = [t for t in enriched if t[2]]
                assigned_now.sort(key=lambda tup: (tup[1], -tup[3]))  # closer and larger streak first to keep stable ones
                for tup in assigned_now:
                    if len(chosen) >= n:
                        break
                    chosen.append(tup[0])
                if len(chosen) < n:
                    others = [t for t in enriched if not t[2]]
                    others.sort(key=lambda tup: (tup[1], tup[3]))  # closer and smaller streak preferred to move
                    for tup in others:
                        if len(chosen) >= n:
                            break
                        chosen.append(tup[0])
            return chosen

        # Start with all drones available
        available = list(drones)

        # Primary allocation: ensure primary is fully protected if possible.
        primary_need = int(primary.drones_for_full_protection)
        # If primary_need > total_drones, we'll assign all drones to primary (best effort)
        to_assign_primary = min(primary_need, total_drones)
        chosen_primary = pick_n_for_field(primary, available, to_assign_primary, primary_field=True)
        for d in chosen_primary:
            assignments[d['key']] = f"protecting {primary.id}"
        # remove chosen from available
        chosen_keys = set(d['key'] for d in chosen_primary)
        available = [d for d in available if d['key'] not in chosen_keys]

        # Allocate for the other selected fields (full protection)
        for field in selected_fields:
            if field.id == primary.id:
                continue
            need = int(field.drones_for_full_protection)
            # If not enough available to fully protect, skip here; we'll handle filling to half later.
            if len(available) >= need:
                chosen = pick_n_for_field(field, available, need, prefer_keep_assigned=True, primary_field=False)
                for d in chosen:
                    assignments[d['key']] = f"protecting {field.id}"
                chosen_keys = set(d['key'] for d in chosen)
                available = [d for d in available if d['key'] not in chosen_keys]
            else:
                # Not enough to fully protect this field now => skip (we prefer full protection)
                continue

        # Count protecting drones so far
        protecting_count = sum(1 for v in assignments.values() if v != 'idle')

        # Ensure at least half the drones are used for protection when possible
        min_protectors = math.ceil(total_drones / 2.0)
        if protecting_count < min_protectors and available:
            needed_more = min_protectors - protecting_count
            # Try to fill remaining needed_more by assigning to next-best fields (could be partial)
            # Build list of candidate fields (not already selected or maybe selected but not fully filled)
            # We'll consider all fields by density that are not already fully filled
            remaining_field_info = []
            # compute already_assigned_to_field based on assignments and current observed assigned counts
            assigned_now_map = {}
            for f in fields:
                # count how many already assigned in our assignments to this field
                assigned_now_map[f.id] = sum(1 for k, g in assignments.items() if g == f"protecting {f.id}")
            # fields not yet fully protected: remaining capacity = drones_for_full_protection - assigned_now_map
            for f in fields:
                remaining_capacity = max(0, int(f.drones_for_full_protection) - assigned_now_map.get(f.id, 0))
                if remaining_capacity > 0:
                    density = f.threat_level / max(1, f.drones_for_full_protection)
                    remaining_field_info.append((f, remaining_capacity, density))
            # sort by density desc
            remaining_field_info.sort(key=lambda t: t[2], reverse=True)
            # Now iterate and assign needed_more drones to best fields, preferring to fill existing selected fields first
            for (f, rem_cap, _) in remaining_field_info:
                if needed_more <= 0 or not available:
                    break
                take = min(rem_cap, needed_more, len(available))
                if take <= 0:
                    continue
                chosen = pick_n_for_field(f, available, take, prefer_keep_assigned=(f in selected_fields), primary_field=(f.id==primary.id))
                for d in chosen:
                    assignments[d['key']] = f"protecting {f.id}"
                chosen_keys = set(d['key'] for d in chosen)
                available = [d for d in available if d['key'] not in chosen_keys]
                needed_more -= len(chosen)
            # update protecting_count
            protecting_count = sum(1 for v in assignments.values() if v != 'idle')

        # Any remaining available drones -> assign to idle
        for d in available:
            assignments[d['key']] = 'idle'

        # As a safety (and to satisfy rule "If a component is supposed to remain in the same group it must always be explicitly re-assigned"),
        # ensure every drone is assigned explicitly
        for d in drones:
            key = d['key']
            if key not in assignments:
                assignments[key] = 'idle'

        # Finally, apply assignments and update per-drone streaks
        for d in drones:
            comp = d['comp']
            key = d['key']
            group = assignments.get(key, 'idle')
            environment.assign_group(comp, group)
            if self.last_group.get(key) == group:
                self.streaks[key] = self.streaks.get(key, 0) + 1
            else:
                self.streaks[key] = 1
            self.last_group[key] = group
```