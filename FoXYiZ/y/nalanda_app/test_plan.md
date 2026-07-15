# Test plan — nalanda_app

## Summary

Test plan for Nalanda SkillFlow AI launch readiness focusing on core routes and UX validation.

## Coverage

- **7** automated (`Run=Y`) · **6** manual (`Run=N`) · **13** plans in y1Plans.

## User stories

- **Core Route Exploration** (automated) — As a user, I want to explore the core routes of the app to ensure they are functioning correctly.
- **Learning Path Functionality** (automated) — As a user, I want to access and utilize the learning paths to enhance my learning experience.
- **Quiz Interaction** (automated) — As a user, I want to take quizzes to assess my knowledge and skills.
- **AI Tutor Engagement** (automated) — As a user, I want to interact with the AI Tutor for personalized learning assistance.
- **UX Gap Identification** (manual) — As a QA Hunter, I want to identify any UX gaps in the application for improvement.

## Test cases (BRAHL draft)

- `T1` Smoke Test: Explore Route [auto]
- `T2` Smoke Test: Learning Path Access [auto]
- `T3` Smoke Test: Quiz Functionality [auto]
- `T4` Smoke Test: AI Tutor Interaction [auto]
- `T5` Manual UX Test: Explore Route [manual]
- `T6` Manual UX Test: Learning Path Navigation [manual]
- `T7` Manual UX Test: Quiz User Experience [manual]
- `T8` Manual UX Test: AI Tutor Usability [manual]
- `T9` Performance Test: Load on Core Routes [auto]
- `T10` Security Test: User Data Protection [auto]
- `T11` Accessibility Test: Screen Reader Compatibility [manual]
- `T12` Cross-Browser Test: Core Routes [auto]

## yPAD plans (`y1Plans.csv`)

| PlanId | PlanName | Run | Tags |
| --- | --- | --- | --- |
| PReuse_NalandaApp_OpenSite | Open browser and navigate to nalanda_app | N | Reuse |
| PNalandaApp_T1_Smoke_Test_Explore_Route | Smoke Test: Explore Route | Y | nalanda_app;Smoke;BRAHL;T1 |
| PNalandaApp_T2_Smoke_Test_Learning_Path_ | Smoke Test: Learning Path Access | Y | nalanda_app;Smoke;BRAHL;T2 |
| PNalandaApp_T3_Smoke_Test_Quiz_Functiona | Smoke Test: Quiz Functionality | Y | nalanda_app;Smoke;BRAHL;T3 |
| PNalandaApp_T4_Smoke_Test_AI_Tutor_Inter | Smoke Test: AI Tutor Interaction | Y | nalanda_app;Smoke;BRAHL;T4 |
| PNalandaApp_T9_Performance_Test_Load_on_ | Performance Test: Load on Core Routes | Y | nalanda_app;Smoke;BRAHL;T9 |
| PNalandaApp_T10_Security_Test_User_Data_ | Security Test: User Data Protection | Y | nalanda_app;Smoke;BRAHL;T10 |
| PNalandaApp_T12_Cross_Browser_Test_Core_ | Cross-Browser Test: Core Routes | Y | nalanda_app;Smoke;BRAHL;T12 |
| PNalandaApp_Man_T5_Manual_UX_Test_Explore_Ro | Manual UX Test: Explore Route | N | nalanda_app;Manual;T5 |
| PNalandaApp_Man_T6_Manual_UX_Test_Learning_P | Manual UX Test: Learning Path Navigation | N | nalanda_app;Manual;T6 |
| PNalandaApp_Man_T7_Manual_UX_Test_Quiz_User_ | Manual UX Test: Quiz User Experience | N | nalanda_app;Manual;T7 |
| PNalandaApp_Man_T8_Manual_UX_Test_AI_Tutor_U | Manual UX Test: AI Tutor Usability | N | nalanda_app;Manual;T8 |
| PNalandaApp_Man_T11_Accessibility_Test_Scree | Accessibility Test: Screen Reader Compatibility | N | nalanda_app;Manual;T11 |

## How to run

Execute via FoXYiZ fEngine2 — low-code Tests/Steps/Test data CSVs. No Playwright.

_Source: `y/nalanda_app/test_plan.md` (synthesized if the file was missing)._