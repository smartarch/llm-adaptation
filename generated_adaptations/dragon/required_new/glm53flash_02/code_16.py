from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    EAT_AT = 5          # eat in village when this hungry (starving starts at 6)
    LEAVE_CAVE_AT = 4   # leave cave at 4 -> arrive at 5 -> eat -> safe
    WARRIOR_CAP = 18

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        total_warriors = len(environment.warriors)
        total_villagers = total_warriors + len(environment.farmers)
        dragon_hp = environment.dragon.hp

        assault = total_warriors >= 4 or step >= 10
        late = step >= 20
        # finisher: dragon nearly dead, squeeze extra attacks
        finisher = assault and dragon_hp <= 4 * max(1, total_warriors)

        hungry_count = sum(1 for c in components if c.steps_since_meal >= self.EAT_AT)

        # ---- spawn planning (with food reserve) ----
        reserve = hungry_count + 4
        budget = max(0, wheat - reserve)
        f_pairs = 0
        w_pairs = 0
        if step < 5 and total_villagers < 10:
            f_pairs = max(0, min(2, (budget - 20) // 10))
            budget -= f_pairs * 10
        if total_warriors < self.WARRIOR_CAP:
            w_pairs = max(0, min(4, budget // 12))
            budget -= w_pairs * 12

        w_left = w_pairs * 2
        f_left = f_pairs * 2

        for c in components:
            # 1) eating has top priority, always
            if c.steps_since_meal >= self.EAT_AT and wheat > 0:
                environment.assign_group(c, "eat")
                wheat -= 1
                continue

            # 2) spawn duties (complete pairs only)
            if w_left >= 2:
                environment.assign_group(c, "spawn warrior")
                w_left -= 1
                wheat -= 6
                continue
            if f_left >= 2:
                environment.assign_group(c, "spawn farmer")
                f_left -= 1
                wheat -= 5
                continue

            # 3) warriors: attack during assault
            if c.role == "Warrior":
                environment.assign_group(c, "cave" if (assault or late) else "farm")
                continue

            # 4) farmers: mostly farm; surplus joins the assault when rich
            if late and c.steps_since_meal <= 2 and wheat >= 8:
                environment.assign_group(c, "cave")
            elif assault and total_warriors >= 6 and wheat >= 40 and c.steps_since_meal <= 2:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp
        attackers = [c for c in components if c.steps_since_meal < self.LEAVE_CAVE_AT]
        finisher = dragon_hp <= 3 * max(1, len(attackers))

        for c in components:
            # absolute safety: never let a villager reach hunger 6
            if c.steps_since_meal >= self.LEAVE_CAVE_AT and not (finisher and c.steps_since_meal < self.LEAVE_CAVE_AT + 1):
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")