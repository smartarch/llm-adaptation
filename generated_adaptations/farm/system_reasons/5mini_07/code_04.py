from typing import Dict, Any, List, Tuple
import math

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # history: drone_key -> {"group": group_id, "since": step}
        self._history: Dict[Any, Dict[str, Any]] = {}
        # drone speed (provided in the problem statement)
        self._drone_speed = 2.0

    def _drone_key(self, component):
        # Prefer a stable 'id' attribute if present, otherwise use Python id()
        return getattr(component, "id", id(component))

    def _field_center(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return cx, cy

    def _distance(self, loc, fx, fy):
        dx = (getattr(loc, "x", 0.0) - fx)
        dy = (getattr(loc, "y", 0.0) - fy)
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Initialize history entries for drones using observed state if missing
        drone_infos: Dict[Any, Dict[str, Any]] = {}
        for comp in components:
            key = self._drone_key(comp)
            if key not in self._history:
                # Try to infer observed group from component.state and target_id
                state = getattr(comp, "state", None)
                target = getattr(comp, "target_id", None)
                if state == "protecting" and target is not None:
                    inferred = f"protecting {target}"
                else:
                    inferred = "idle"
                self._history[key] = {"group": inferred, "since": step}
            drone_infos[key] = {
                "component": comp,
                "last_group": self._history[key]["group"],
                "since": self._history[key]["since"],
            }

        total_drones = len(components)
        min_protectors_target = math.ceil(total_drones / 2)

        # Gather threatened fields
        fields = [f for f in getattr(environment, "fields", []) if getattr(f, "threat_level", 0) > 0]
        if not fields:
            # No threatened fields: put everyone idle
            for comp in components:
                environment.assign_group(comp, "idle")
                key = self._drone_key(comp)
                if self._history.get(key, {}).get("group") != "idle":
                    self._history[key] = {"group": "idle", "since": step}
            return

        # Sort to find top threatened field (highest threat)
        fields_sorted_by_threat = sorted(fields, key=lambda f: getattr(f, "threat_level", 0), reverse=True)
        top_field = fields_sorted_by_threat[0]

        # Helper: compute a score for every drone for a particular field based on arrival time and change penalty
        def scored_candidates_for_field(field) -> List[Tuple[Any, float, float, float, int]]:
            fx, fy = self._field_center(field)
            candidates = []
            for key, info in drone_infos.items():
                comp = info["component"]
                dist = self._distance(comp.location, fx, fy)
                arrival_time = dist / self._drone_speed
                last_group = info["last_group"]
                since = info["since"]
                since_steps = max(0, step - since)
                desired_group = f"protecting {field.id}"

                # Base penalty for changing assignments (stronger than before but capped)
                # If already assigned to desired_group -> zero penalty.
                # If moving_to_field toward desired field -> small negative bonus (favor it).
                if last_group == desired_group:
                    change_penalty = 0.0
                else:
                    # penalty grows with time stayed in current group but capped to avoid dominating arrival_time
                    base_penalty = 0.06  # tuned small constant
                    max_penalty = 3.0
                    change_penalty = min(max_penalty, base_penalty * float(since_steps))

                state = getattr(comp, "state", None)
                target = getattr(comp, "target_id", None)
                # bonus for drone already moving to this field (it will arrive soon)
                moving_bonus = 0.0
                if state == "moving_to_field" and target == field.id:
                    moving_bonus = -0.25  # favor these drones
                # small bonus if currently protecting that field (already accounted via change_penalty == 0)
                # Composite score: arrival_time plus change_penalty and moving bonus
                score = arrival_time + change_penalty + moving_bonus
                candidates.append((key, score, arrival_time, change_penalty, since_steps))
            # sort by score (lower better), tie-break by arrival_time, prefer longer-serving otherwise
            candidates.sort(key=lambda x: (x[1], x[2], -x[4]))
            return candidates

        # Allocation bookkeeping
        allocation: Dict[str, List[Any]] = {}
        assigned_keys = set()

        def allocate_best_for_field(field, k):
            """Allocate exactly k drones (or as many as available) to fully protect field, return chosen keys."""
            desired_group = f"protecting {field.id}"
            if desired_group not in group_ids:
                return []
            if k <= 0:
                return []
            candidates = scored_candidates_for_field(field)
            chosen: List[Any] = []
            # Prefer drones already in desired_group first (stability)
            already = [c for c in candidates if drone_infos[c[0]]["last_group"] == desired_group and c[0] not in assigned_keys]
            # Sort those by longest-serving (smallest since value)
            already_sorted = sorted(already, key=lambda x: (x[3],))
            for tup in already_sorted:
                if len(chosen) >= k:
                    break
                key = tup[0]
                chosen.append(key)
                assigned_keys.add(key)
            # Fill remaining from candidates
            if len(chosen) < k:
                for key, _, _, _, _ in candidates:
                    if key in assigned_keys:
                        continue
                    chosen.append(key)
                    assigned_keys.add(key)
                    if len(chosen) >= k:
                        break
            allocation.setdefault(desired_group, []).extend(chosen)
            return chosen

        # 1) Fully protect the top field
        need_top = max(0, int(getattr(top_field, "drones_for_full_protection", 0)))
        need_top = min(need_top, total_drones)
        allocate_best_for_field(top_field, need_top)

        # 2) Consider other fields by benefit-per-drone (threat_level / drones_needed)
        other_fields = fields_sorted_by_threat[1:]
        def benefit_metric(field):
            need = max(1, int(getattr(field, "drones_for_full_protection", 1)))
            return float(getattr(field, "threat_level", 0)) / float(need)

        other_fields_sorted = sorted(other_fields, key=benefit_metric, reverse=True)

        # Try to fully protect additional fields until we reach min_protectors_target or run out
        for field in other_fields_sorted:
            protected_count = sum(len(v) for v in allocation.values())
            if protected_count >= min_protectors_target:
                break
            need = max(0, int(getattr(field, "drones_for_full_protection", 0)))
            remaining = total_drones - len(assigned_keys)
            if need <= 0 or need > remaining:
                continue  # skip if cannot fully protect
            allocate_best_for_field(field, need)

        # 3) If we still haven't reached half the drones protecting, consider allowing a single partial allocation
        protected_count = sum(len(v) for v in allocation.values())
        remaining = total_drones - len(assigned_keys)
        if protected_count < min_protectors_target and remaining > 0:
            # Find the best remaining field to give partial protection such that we reach at least the target
            # Evaluate candidate fields that are not yet fully protected
            needed_more = min_protectors_target - protected_count
            best_choice = None
            best_score = float("inf")
            for field in other_fields_sorted:
                g = f"protecting {field.id}"
                already_assigned = len(allocation.get(g, []))
                need_full = max(0, int(getattr(field, "drones_for_full_protection", 0)))
                # only consider fields with some required drones (and not already fully protected)
                if need_full <= 0 or already_assigned >= need_full:
                    continue
                # number we could allocate to this field now (capped)
                allocate_count = min(remaining, needed_more)
                # compute score for allocating allocate_count drones (use sum of top allocate_count candidate scores)
                candidates = scored_candidates_for_field(field)
                # exclude already assigned drones
                candidates = [c for c in candidates if c[0] not in assigned_keys]
                if not candidates:
                    continue
                # sum top allocate_count arrival_time+penalty
                top_slice = candidates[:allocate_count]
                if len(top_slice) < allocate_count:
                    continue
                score_sum = sum(c[1] for c in top_slice)
                # penalize when allocate_count is less than needed for full protection (partial)
                partial_penalty = 0.5 * (1.0 - float(allocate_count) / max(1, need_full))
                score_sum += partial_penalty
                if score_sum < best_score:
                    best_score = score_sum
                    best_choice = (field, allocate_count)
            # If we found a worthwhile partial allocation, apply it (as last resort)
            if best_choice is not None:
                fld, cnt = best_choice
                # allocate cnt drones even though it's partial
                desired_group = f"protecting {fld.id}"
                # pick top cnt candidates
                cands = scored_candidates_for_field(fld)
                picks = []
                for key, _, _, _, _ in cands:
                    if key in assigned_keys:
                        continue
                    picks.append(key)
                    assigned_keys.add(key)
                    if len(picks) >= cnt:
                        break
                allocation.setdefault(desired_group, []).extend(picks)

        # 4) Trim any accidental over-allocation (shouldn't usually happen)
        for field in fields:
            g = f"protecting {field.id}"
            if g in allocation:
                max_needed = max(0, int(getattr(field, "drones_for_full_protection", 0)))
                if len(allocation[g]) > max_needed:
                    kept = allocation[g]
                    # prefer drones with longer-serving since (smaller since value)
                    kept_sorted = sorted(kept, key=lambda k: (drone_infos[k]["since"],))
                    allocation[g] = kept_sorted[:max_needed]
                    for freed in kept_sorted[max_needed:]:
                        assigned_keys.discard(freed)

        # 5) Assign remaining drones to idle
        final_assignments: Dict[Any, str] = {}
        for key in drone_infos:
            assigned_group = None
            for g, keys in allocation.items():
                if key in keys:
                    assigned_group = g
                    break
            if assigned_group is None:
                assigned_group = "idle"
            final_assignments[key] = assigned_group

        # 6) Commit assignments and update history
        for key, info in drone_infos.items():
            comp = info["component"]
            group = final_assignments[key]
            if group not in group_ids:
                # fall back to idle if invalid
                group = "idle"
            environment.assign_group(comp, group)
            prev = self._history.get(key)
            if prev is None or prev.get("group") != group:
                # new assignment: update since
                self._history[key] = {"group": group, "since": step}
            # else keep previous 'since' to reflect continuous assignment