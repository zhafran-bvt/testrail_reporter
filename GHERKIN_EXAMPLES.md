# Gherkin Parsing Examples

## Example 1: Basic Login Scenario

### Before (JSON Stringify Format)
```json
[{"content":"Given user is on login page\\nWhen user enters valid credentials\\nAnd user clicks login button\\nThen user is redirected to dashboard"}]
```

### After (Formatted Gherkin)
```gherkin
Given user is on login page
When user enters valid credentials
  And user clicks login button
Then user is redirected to dashboard
```

---

## Example 2: Complex Scenario with Multiple Steps

### Before (JSON Stringify Format)
```json
[{"content":"Given user logged in\\nAnd user navigated to analysis page\\nAnd user selected project ORB\\nWhen user clicks run analysis button\\nAnd system processes the data\\nThen analysis results are displayed\\nAnd user can download the report"}]
```

### After (Formatted Gherkin)
```gherkin
Given user logged in
  And user navigated to analysis page
  And user selected project ORB
When user clicks run analysis button
  And system processes the data
Then analysis results are displayed
  And user can download the report
```

---

## Example 3: Scenario with But Keyword

### Before (JSON Stringify Format)
```json
[{"content":"Given user has admin privileges\\nWhen user tries to delete a test run\\nBut the run has test results\\nThen system shows warning message\\nAnd deletion is prevented"}]
```

### After (Formatted Gherkin)
```gherkin
Given user has admin privileges
When user tries to delete a test run
  But the run has test results
Then system shows warning message
  And deletion is prevented
```

---

## Example 4: API Testing Scenario

### Before (JSON Stringify Format)
```json
[{"content":"Given API endpoint is available\\nAnd authentication token is valid\\nWhen POST request is sent with valid payload\\nThen response status is 200\\nAnd response contains expected data\\nAnd database is updated"}]
```

### After (Formatted Gherkin)
```gherkin
Given API endpoint is available
  And authentication token is valid
When POST request is sent with valid payload
Then response status is 200
  And response contains expected data
  And database is updated
```

---

## Example 5: Error Handling Scenario

### Before (JSON Stringify Format)
```json
[{"content":"Given user is not authenticated\\nWhen user tries to access protected resource\\nThen system returns 403 error\\nAnd user is redirected to login page"}]
```

### After (Formatted Gherkin)
```gherkin
Given user is not authenticated
When user tries to access protected resource
Then system returns 403 error
  And user is redirected to login page
```

---

## Example 6: Data-Driven Scenario

### Before (JSON Stringify Format)
```json
[{"content":"Given user is on registration page\\nWhen user enters email test@example.com\\nAnd user enters password SecurePass123\\nAnd user confirms password SecurePass123\\nAnd user clicks register button\\nThen account is created successfully\\nAnd confirmation email is sent"}]
```

### After (Formatted Gherkin)
```gherkin
Given user is on registration page
When user enters email test@example.com
  And user enters password SecurePass123
  And user confirms password SecurePass123
  And user clicks register button
Then account is created successfully
  And confirmation email is sent
```

---

## Example 7: Mobile App Scenario

### Before (JSON Stringify Format)
```json
[{"content":"Given mobile app is installed\\nAnd user is logged in\\nWhen user navigates to settings\\nAnd user enables dark mode\\nThen UI switches to dark theme\\nAnd preference is saved"}]
```

### After (Formatted Gherkin)
```gherkin
Given mobile app is installed
  And user is logged in
When user navigates to settings
  And user enables dark mode
Then UI switches to dark theme
  And preference is saved
```

---

## Example 8: Integration Test Scenario

### Before (JSON Stringify Format)
```json
[{"content":"Given payment gateway is configured\\nAnd user has items in cart\\nWhen user proceeds to checkout\\nAnd user enters payment details\\nAnd user confirms payment\\nThen payment is processed\\nAnd order confirmation is sent\\nAnd inventory is updated"}]
```

### After (Formatted Gherkin)
```gherkin
Given payment gateway is configured
  And user has items in cart
When user proceeds to checkout
  And user enters payment details
  And user confirms payment
Then payment is processed
  And order confirmation is sent
  And inventory is updated
```

---

## Notes

- **Indentation**: Main keywords (Given/When/Then) are left-aligned, continuation keywords (And/But) are indented with 2 spaces
- **Readability**: The formatted version is much easier to read and understand
- **Editing**: Users can now edit BDD scenarios in a natural, readable format
- **Compatibility**: The formatted text is saved back to TestRail and works with existing data
