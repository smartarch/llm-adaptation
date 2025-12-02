Here is a report from running unit tests on your implementation:

...F...F.sssssssssss                                                     [100%]
================================== FAILURES ===================================
_____________________ TestAdapt.test_no_assignment_errors _____________________
There were 1 assignment errors in total.
_________________ TestAdapt.test_no_user_constraints_violated _________________
The most threatened field should be fully protected (Field_1, threat level 0.16, 4 drones for full protection, 3 assigned).
=================================== PASSES ====================================
___________________ TestAdapt.test_no_repeated_assignments ____________________
______________________ TestAdapt.test_no_invalid_groups _______________________
_________________________ TestAdapt.test_all_assigned _________________________
___________ TestAdapt.test_no_user_constraints_violated_at_the_end ____________
=========================== short test summary info ===========================
FAILED TestAdapt::test_no_assignment_errors - Failed: There were 1 assignment...
FAILED TestAdapt::test_no_user_constraints_violated - Failed: The most threat...
PASSED TestConfiguration::test_example_is_correct
PASSED TestConfiguration::test_adaptation_exists
PASSED TestConfiguration::test_adaptation_class_is_correct
PASSED TestAdapt::test_no_repeated_assignments
PASSED TestAdapt::test_no_invalid_groups
PASSED TestAdapt::test_all_assigned
PASSED TestAdapt::test_no_user_constraints_violated_at_the_end
2 failed, 7 passed, 11 skipped in 3.79s

Update your code to fix the failing tests.
