# Offline prompting results - generated strategies

## Farm

[generate_and_run_farm.ipynb](generate_and_run_farm.ipynb)

### Variants

* [farm_sd2](prompts/farm_sd2.txt) -- default
* [farm_sd2_strategy](prompts/farm_sd2_strategy.txt) -- hinted strategy (in natural language)
* [farm_sd2_step-by-step](prompts/farm_sd2_step-by-step.txt) -- step by step strategy

We have three repetitions for each run, suffixed by 2, 3, 4 (note that suffix 1 refers to an early experimentation).

### Results

#### Common mistakes of LLMs

We noticed several mistakes that were common among the generated strategies. Here is a list of them with the prompts that we used to point these mistakes out to the LLM to fix the strategy.

##### Removes from protection

In your strategy, you compute how many additional drones are necessary for full protection, assuming currently protecting drones will keep protecting. However, the currently protecting drones are also among the components to be assigned. Therefore, when assigning the drones, you then reassign the currently protecting drones to the "idle" group, which removes them from protection. If you want the drone to keep protecting the field, make sure to assign it again to the associated “protecting” group.

##### Idle only

You are assigning only the idle drones. In order to adapt to the current situation, you might also need to update and reassign the drones that already protect (or move towards) fields.

##### Not using all

The protection of the most threatened field work well. However, you can improve the protection by assigning the remaining drones to other fields instead of keeping them idle.

##### Multiple assignments

You are assigning a drone to multiple groups. Each drone must be assigned exactly once. You cannot override an assignment that was already made.

##### Count twice

When computing the number of additional drones necessary for full protection of the most threatened field, you already account for the protecting and arriving drones. When assigning these drones to keep protecting the field, you should not subtract them again from the required number of drones (to prevent counting them twice).

#### OpenAI o3-mini

##### Default

2. *removes from protection*
3. *removes from protection*
4. *removes from protection*

##### Hinted

2. *removes from protection*
3. *not using all*
4. *not using all*

##### Step-by-step

2. When computing the `already_assigned_main`, you consider the protecting and arriving drones. However, when assigning the `already_protecting`, you forgot to consider the arriving drones.
3. *count twice*
4. *multiple assignments*

#### GPT-4o

##### Default

2. *idle only*
3. *idle only*
4. *idle only*

##### Hinted

2. *idle only*
3. *idle only*
4. *idle only*

##### Step-by-step

2. *count twice*
3. *count twice*
4. *idle only*

## Dragon

[generate_and_run_dragon.ipynb](generate_and_run_dragon.ipynb)