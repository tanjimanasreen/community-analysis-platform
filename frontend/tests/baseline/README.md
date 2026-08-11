# Frontend baseline capture

The current route-to-component map is:

| Route | Component |
|---|---|
| `/` | `Overview` |
| `/communities` | `CommunitiesPage` |
| `/network` | Redirects to `/communities` with query parameters preserved |
| `/thematic` | `ThematicAnalysisPage` |
| `/evolution` | `CommunityEvolutionPage` |
| `/run-history` | `EvolutionOverTimePage` |
| `/comparative` | `ComparativeAnalysisPage` |
| `/transitions` | Redirects to `/evolution` with query parameters preserved |
| `/top-communities` | Redirects to `/communities` with query parameters preserved |
| `/data-reports` | `EvidencePage` (Research Data & Reports) |
| `/evidence` | Redirects to `/data-reports` with query parameters and explicit `view` preserved |
| `/data` | Redirects to `/data-reports?view=communities` when `view` is absent |
| `/reports` | Redirects to `/data-reports?view=outputs` when `view` is absent |
| `/methodology` | `MethodologyPage` |

Binary screenshot fixtures are not checked in for Plan 026. Capture desktop and
mobile baselines outside version control with the application running:

```bash
npx playwright screenshot --viewport-size=1440,1000 http://127.0.0.1:5173/ overview-desktop.png
npx playwright screenshot --viewport-size=390,844 http://127.0.0.1:5173/ overview-mobile.png
```

Repeat the command for each route above. Later visual-regression work may adopt
checked-in images after repository policy is defined.
