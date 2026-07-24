# Test plan — Math

## Summary

Test plan for Math application to ensure functionality and performance of mathematical operations.

## Coverage

- **8** automated (`Run=Y`) · **5** manual (`Run=N`) · **13** plans in y1Plans.

## User stories

- **Basic Arithmetic Operations** (automated) — As a user, I want to perform basic arithmetic operations (addition, subtraction, multiplication, division) so that I can solve simple math problems.
- **Advanced Mathematical Functions** (automated) — As a user, I want to use advanced functions (square root, exponentiation) to solve complex equations.
- **Graphing Functions** (manual) — As a user, I want to graph mathematical functions to visualize relationships between variables.
- **User Input Validation** (automated) — As a user, I want to receive feedback on invalid inputs to ensure I enter correct data.
- **Mobile Responsiveness** (manual) — As a user, I want the app to be responsive on mobile devices for accessibility.

## Test cases (BRAHL draft)

- `T1` Test Addition Functionality [auto]
- `T2` Test Subtraction Functionality [auto]
- `T3` Test Multiplication Functionality [auto]
- `T4` Test Division Functionality [auto]
- `T5` Test Square Root Functionality [auto]
- `T6` Test Exponentiation Functionality [auto]
- `T7` Test Graphing Linear Functions [manual]
- `T8` Test Graphing Quadratic Functions [manual]
- `T9` Test Invalid Input Handling [auto]
- `T10` Test Mobile Layout [manual]
- `T11` Test Performance of Calculations [auto]
- `T12` Test User Interface for Accessibility [manual]

## yPAD plans (`y1Plans.csv`)

| PlanId | PlanName | Run | Tags |
| --- | --- | --- | --- |
| PReuse_Math_OpenSite | Open browser and navigate to math | N | Reuse |
| PMath_T1_Test_Addition_Functionali | Test Addition Functionality | Y | math;Smoke;BRAHL;T1 |
| PMath_T2_Test_Subtraction_Function | Test Subtraction Functionality | Y | math;Smoke;BRAHL;T2 |
| PMath_T3_Test_Multiplication_Funct | Test Multiplication Functionality | Y | math;Smoke;BRAHL;T3 |
| PMath_T4_Test_Division_Functionali | Test Division Functionality | Y | math;Smoke;BRAHL;T4 |
| PMath_T5_Test_Square_Root_Function | Test Square Root Functionality | Y | math;Smoke;BRAHL;T5 |
| PMath_T6_Test_Exponentiation_Funct | Test Exponentiation Functionality | Y | math;Smoke;BRAHL;T6 |
| PMath_T9_Test_Invalid_Input_Handli | Test Invalid Input Handling | Y | math;Smoke;BRAHL;T9 |
| PMath_T11_Test_Performance_of_Calc | Test Performance of Calculations | Y | math;Smoke;BRAHL;T11 |
| PMath_Man_T7_Test_Graphing_Linear_Func | Test Graphing Linear Functions | N | math;Manual;T7 |
| PMath_Man_T8_Test_Graphing_Quadratic_F | Test Graphing Quadratic Functions | N | math;Manual;T8 |
| PMath_Man_T10_Test_Mobile_Layout | Test Mobile Layout | N | math;Manual;T10 |
| PMath_Man_T12_Test_User_Interface_for_ | Test User Interface for Accessibility | N | math;Manual;T12 |

## How to run

Execute via FoXYiZ fEngine2 — low-code Tests/Steps/Test data CSVs. No Playwright.

_Source: `y/Math/test_plan.md` (synthesized if the file was missing)._