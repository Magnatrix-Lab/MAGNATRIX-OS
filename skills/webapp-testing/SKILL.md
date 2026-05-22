---
name: webapp-testing
agent: architect
description: Run targeted web app tests dan summarize results untuk quality assurance
schedule: "*/30 * * * *"
---

# webapp-testing

## Objective
Automated testing untuk MAGNATRIX web components (dashboard, API gateway, website) dengan Playwright atau similar.

## Steps
1. Identify test targets: dashboard URLs, API endpoints, website pages.
2. Generate test cases berdasarkan user flows: login, data visualization, API calls.
3. Execute tests: screenshot comparison, API response validation, performance timing.
4. Record results: pass/fail, error screenshots, response times.
5. Cek regression: compare dengan baseline dari run sebelumnya.
6. Jika regression detected, flag affected component dan route ke ops.
7. Generate test summary report.
8. Store results ke knowledge graph.
9. Broadcast ke mesh jika critical failure.

## Output
- Test report: {tests_run, pass_rate, regressions, avg_response_time}
- Screenshots (jika visual regression)
- Mesh broadcast: msg_type=TEST_RESULTS

## Exit Codes
- SKILL_OK: All tests pass atau no regression
- SKILL_WARN: Some failures tapi non-critical
- SKILL_FAIL: Critical regression atau test infrastructure error
