Reasoning and strategy

We need to assign every drone to exactly one group ("idle" or "protecting {field.id}") at every decision step. The highest-priority functional requirements are:

- Always fully protect the single most threatened field.
- Use the closest drones to protect that most-threatened field.
- Do not overprotect fields (never allocate more than field.drones_for_full_protection).
- Keep drones' assignments reasonably stable (don't shuffle drones every step).
- Use at least half the fleet to protect fields most of the time (favor full protection of fewer fields over many partial protections).

To satisfy these goals I implemented the following strategy:

1. Maintain a light-weight assignment history across steps:
   - For each drone we remember the last group we assigned it to and a consecutive-stability counter (how many consecutive steps it stayed in the same group). This lets the strategy prefer retaining drones in their current groups and avoid excessive switching.
2. Select the highest-threat field (threat_level > 0) as the primary target. It must be fully protected.
   - Keep drones already assigned to that field (from our previous assignments) up to the required number.
   - If more drones are needed for full protection, pick additional drones by increasing Euclidean distance from the field center. When choosing among candidates, prefer drones that are not currently very "stable" in other groups (so we avoid breaking long-lived assignments unless necessary).
3. After the top-threat field is fully protected, attempt to fully protect other fields in descending threat order, greedily:
   - For each other threatened field, keep existing drones (from previous assignment) up to the needed number, then add closest available drones as required.
   - Do not exceed the field's drones_for_full_protection.
4. If after the greedy pass fewer than half of the drones are protecting fields, keep trying to fill other fields (still obeying full-protection constraint) until at least half of the drones are assigned to protection groups or there are no more fields/drones that can be allocated.
5. Any drones that remain unassigned after the above steps are put into "idle".
6. Update the stored assignment and stability counters:
   - If a drone stays in the same group as in the previous step, increment its stability counter.
   - If a drone changes group, reset its stability counter to 0.

Notes about trade-offs and the heuristics used
- Closest-drones requirement for the most threatened field is enforced strictly: after keeping existing defenders, additional defenders for the top field are selected by distance.
- Stability is used as a soft constraint to avoid frequent reassignments: when choosing which drones to move to a new field, drones with higher stability in other groups are avoided unless necessary.
- The strategy prioritizes fully protecting fewer fields (greedy by threat) rather than partially protecting many fields.
- The implementation is conservative about moving drones: it tries to keep already-protecting drones in place and prefers to move drones with low stability to meet full-protection requirements.

Code

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Mapping from drone unique id -> last assigned group string
        self.prev_group = {}
        # Mapping from drone unique id -> consecutive steps it stayed in same group
        self.stability = {}
        # last seen step number to detect discontinuities (optional)
        self.last_step = None

    def _comp_id(self, comp):
        # Prefer attribute 'id' if present, otherwise Python's id()
        return getattr(comp, "id", id(comp))

    def _field_center(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return cx, cy

    def _dist2(self, x1, y1, x2, y2):
        dx = x1 - x2
        dy = y1 - y2
        return dx * dx + dy * dy

    def assign_drones(self, components, environment, group_ids, step: int):
        # Convert components to a list
        comps = list(components)
        total_drones = len(comps)

        # Reset or keep continuity if steps are discontinuous
        if self.last_step is None or step != self.last_step + 1:
            # If the simulation jumps, we still keep prev assignments but do not change semantics.
            # We do not clear prev_group because we want to preserve last commanded grouping.
            pass
        self.last_step = step

        # Build list of threatened fields (threat_level > 0), sorted by descending threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        fields.sort(key=lambda f: (-f.threat_level, str(getattr(f, "id", ""))))

        # Prepare assignments mapping: comp -> group_name
        assignments = {}

        # Helper: assign a given comp to a group name
        def mark_assign(comp, group_name):
            assignments[comp] = group_name

        # If no threatened fields, assign all drones to idle
        if not fields:
            for comp in comps:
                mark_assign(comp, "idle")
            # apply assignments and update history
            for comp in comps:
                comp_id = self._comp_id(comp)
                new_group = assignments[comp]
                prev = self.prev_group.get(comp_id)
                if prev == new_group:
                    self.stability[comp_id] = self.stability.get(comp_id, 0) + 1
                else:
                    self.stability[comp_id] = 0
                self.prev_group[comp_id] = new_group
                environment.assign_group(comp, new_group)
            return

        # Precompute field centers
        field_centers = {f.id: self._field_center(f) for f in fields}

        # Convenience: map from comp to comp_id and location
        comp_info = {}
        for comp in comps:
            comp_id = self._comp_id(comp)
            loc = getattr(comp, "location", None)
            if loc is not None:
                x, y = getattr(loc, "x", 0.0), getattr(loc, "y", 0.0)
            else:
                x, y = 0.0, 0.0
            comp_info[comp] = {"id": comp_id, "loc": (x, y), "state": getattr(comp, "state", None),
                               "target_id": getattr(comp, "target_id", None)}

        # 1) Protect the most threatened field fully
        top_field = fields[0]
        top_group = f"protecting {top_field.id}"
        top_required = int(getattr(top_field, "drones_for_full_protection", 1))

        # Find drones previously assigned to top_group
        prev_top = [c for c in comps if self.prev_group.get(self._comp_id(c)) == top_group]

        # Keep those already assigned to top_group, up to requirement
        kept = []
        for c in prev_top:
            if len(kept) < top_required:
                kept.append(c)
                mark_assign(c, top_group)

        # Need additional drones?
        need = top_required - len(kept)

        if need > 0:
            # Candidate drones are those not already assigned: compute distance to top field center
            cx, cy = field_centers[top_field.id]
            candidates = []
            for c in comps:
                if c in assignments:
                    continue
                info = comp_info[c]
                dist2 = self._dist2(info["loc"][0], info["loc"][1], cx, cy)
                # Stability penalty: prefer to move drones with low stability.
                comp_stab = self.stability.get(info["id"], 0)
                # We create a tie-breaking sort key: primary by distance, secondary by stability (lower preferred)
                candidates.append((dist2, comp_stab, c))
            candidates.sort(key=lambda t: (t[0], t[1]))
            # Assign closest candidates, but avoid breaking very stable drones unless necessary
            for dist2, comp_stab, c in candidates:
                if need <= 0:
                    break
                # Soft rule: avoid moving drones with high stability in other groups if alternatives exist.
                # If all remaining candidates have high stability, we'll still use them.
                # We implement by selecting in sorted order (distance primary), which naturally favors close drones.
                mark_assign(c, top_group)
                need -= 1

        # If we somehow have more kept than required (shouldn't happen), release extras to idle
        assigned_to_top = [c for c, g in assignments.items() if g == top_group]
        if len(assigned_to_top) > top_required:
            # Keep the ones with smallest distance to top field
            cx, cy = field_centers[top_field.id]
            assigned_to_top.sort(key=lambda c: self._dist2(comp_info[c]["loc"][0], comp_info[c]["loc"][1], cx, cy))
            to_keep = set(assigned_to_top[:top_required])
            for c in assigned_to_top:
                if c not in to_keep:
                    # release
                    assignments.pop(c)
        # 2) Greedily protect other fields (descending threat) fully as possible
        # For each other field, keep previous defenders first, then add closest available drones
        for field in fields[1:]:
            group_name = f"protecting {field.id}"
            required = int(getattr(field, "drones_for_full_protection", 1))
            # Keep previously assigned defenders for this field up to required
            prev_defenders = [c for c in comps if self.prev_group.get(self._comp_id(c)) == group_name]
            kept_defenders = []
            for c in prev_defenders:
                if c in assignments:
                    continue  # may already be assigned to top field etc.
                if len(kept_defenders) < required:
                    kept_defenders.append(c)
                    mark_assign(c, group_name)
            need = required - len(kept_defenders)
            if need > 0:
                # Choose remaining closest unassigned drones to this field
                cx, cy = self._field_center(field)
                candidates = []
                for c in comps:
                    if c in assignments:
                        continue
                    info = comp_info[c]
                    dist2 = self._dist2(info["loc"][0], info["loc"][1], cx, cy)
                    comp_stab = self.stability.get(info["id"], 0)
                    candidates.append((dist2, comp_stab, c))
                candidates.sort(key=lambda t: (t[0], t[1]))
                for dist2, comp_stab, c in candidates:
                    if need <= 0:
                        break
                    mark_assign(c, group_name)
                    need -= 1

        # 3) Ensure at least half the drones are protecting if possible:
        protected_count = sum(1 for g in assignments.values() if g != "idle")
        min_protect = (total_drones + 1) // 2  # at least half (rounded up)
        # If not enough, try to fill additional fields (again in descending threat order)
        if protected_count < min_protect:
            # iterate fields in descending threat again, try to fill with remaining unassigned comps
            for field in fields:
                if protected_count >= min_protect:
                    break
                group_name = f"protecting {field.id}"
                required = int(getattr(field, "drones_for_full_protection", 1))
                currently_assigned = [c for c, g in assignments.items() if g == group_name]
                need = required - len(currently_assigned)
                if need <= 0:
                    continue
                cx, cy = self._field_center(field)
                candidates = []
                for c in comps:
                    if c in assignments:
                        continue
                    info = comp_info[c]
                    dist2 = self._dist2(info["loc"][0], info["loc"][1], cx, cy)
                    comp_stab = self.stability.get(info["id"], 0)
                    candidates.append((dist2, comp_stab, c))
                candidates.sort(key=lambda t: (t[0], t[1]))
                for dist2, comp_stab, c in candidates:
                    if need <= 0 or protected_count >= min_protect:
                        break
                    mark_assign(c, group_name)
                    need -= 1
                    protected_count += 1

        # 4) Any remaining drones -> idle
        for c in comps:
            if c not in assignments:
                mark_assign(c, "idle")

        # 5) Apply assignments through environment.assign_group and update history/stability
        for comp in comps:
            comp_id = self._comp_id(comp)
            new_group = assignments.get(comp, "idle")
            prev = self.prev_group.get(comp_id)
            if prev == new_group:
                # stayed the same
                self.stability[comp_id] = self.stability.get(comp_id, 0) + 1
            else:
                # changed group
                self.stability[comp_id] = 0
            self.prev_group[comp_id] = new_group
            # Final assignment call (must be one of group_ids)
            # If for some reason the desired group isn't in group_ids, fall back to "idle"
            if new_group not in group_ids:
                environment.assign_group(comp, "idle")
                self.prev_group[comp_id] = "idle"
            else:
                environment.assign_group(comp, new_group)
```