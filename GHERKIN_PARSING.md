# Gherkin Parsing Feature

## Overview

The TestRail Reporter now automatically converts BDD scenarios from JSON stringify format to readable Gherkin format when editing test cases.

## Problem

TestRail stores BDD scenarios in a JSON stringify format that looks like this:

```json
[{"content":"Given user logged in\\nAnd user navigated to dashboard\\nWhen user clicks button\\nThen result is shown"}]
```

This format is difficult to read and edit directly in the UI.

## Solution

The application now automatically:
1. **Parses** the JSON stringify format when loading test cases
2. **Formats** the content into proper Gherkin syntax with indentation
3. **Displays** the formatted Gherkin in the BDD Scenarios textarea

## How It Works

### Parsing Function (`parseJsonStringifyToGherkin`)

This function:
- Detects if the input is in JSON stringify format
- Extracts the `content` field from the JSON array
- Replaces escaped newlines (`\\n`) with actual newlines
- Ensures all lines start with proper Gherkin keywords (Given/When/Then/And/But)

### Formatting Function (`formatGherkinForDisplay`)

This function:
- Adds proper indentation to Gherkin steps
- Main keywords (Given/When/Then) are left-aligned
- Continuation keywords (And/But) are indented with 2 spaces

## Example Transformation

### Input (JSON Stringify Format)
```json
[{"content":"Given user logged in\\nAnd user navigated to dashboard\\nWhen user clicks button\\nThen result is shown"}]
```

### Output (Formatted Gherkin)
```gherkin
Given user logged in
  And user navigated to dashboard
When user clicks button
Then result is shown
```

## Usage

### In the UI

1. Open a test case for editing
2. The BDD Scenarios field will automatically display formatted Gherkin
3. Edit the scenarios in readable Gherkin format
4. Save changes - the application sends the formatted text to TestRail

### Testing the Parser

A test HTML file is included (`test_gherkin_parsing.html`) that allows you to:
- Test the parsing functions with different inputs
- See the transformation in real-time
- Try example scenarios

To use the test file:
```bash
# Open in browser
open test_gherkin_parsing.html
```

## Technical Details

### Files Modified

1. **src/manage.ts**
   - Added `parseJsonStringifyToGherkin()` function (line ~1413)
   - Added `formatGherkinForDisplay()` function (line ~1466)
   - Modified `showCaseEditModal()` to parse BDD scenarios before display (line ~2970)

2. **templates/index.html**
   - BDD Scenarios textarea uses monospace font for better readability
   - Field ID: `caseEditBddScenarios`

### API Integration

- **GET /api/manage/case/{case_id}**: Returns BDD scenarios in original format
- **PUT /api/manage/case/{case_id}**: Accepts formatted Gherkin text
- Field name: `custom_bdd_scenario`

### Supported Formats

The parser handles:
- ✅ JSON stringify format: `[{"content":"...\\n..."}]`
- ✅ Escaped JSON format: `[{\\"content\\":\\"...\\\\n...\\"}]`
- ✅ Plain text format: Already formatted Gherkin
- ✅ Empty or null values

### Edge Cases

1. **Empty BDD Scenarios**: Returns empty string
2. **Invalid JSON**: Falls back to cleaning up the string
3. **Missing Keywords**: Automatically adds "And" prefix
4. **Mixed Formats**: Handles both escaped and unescaped formats

## Benefits

1. **Improved Readability**: BDD scenarios are displayed in proper Gherkin format
2. **Better UX**: Users can read and edit scenarios naturally
3. **No Data Loss**: Original data is preserved, only display format changes
4. **Backward Compatible**: Works with existing TestRail data

## Future Enhancements

Potential improvements:
- Syntax highlighting for Gherkin keywords
- Auto-completion for common Gherkin steps
- Validation of Gherkin syntax
- Toggle between "raw" and "formatted" view
- Export scenarios to .feature files

## Troubleshooting

### BDD Scenarios Not Formatting

**Issue**: BDD scenarios still show in JSON format

**Solutions**:
1. Check browser console for JavaScript errors
2. Verify `assets/app.js` was rebuilt: `npm run build:ui`
3. Clear browser cache and reload
4. Check that the case has BDD scenarios data

### Formatting Looks Wrong

**Issue**: Indentation or keywords are incorrect

**Solutions**:
1. Check the original data format in TestRail
2. Test the parser with `test_gherkin_parsing.html`
3. Verify the input matches expected JSON stringify format

## Examples

### Example 1: Basic Login Scenario

**Before (JSON Stringify Format)**
```json
[{"content":"Given user is on login page\\nWhen user enters valid credentials\\nAnd user clicks login button\\nThen user is redirected to dashboard"}]
```

**After (Formatted Gherkin)**
```gherkin
Given user is on login page
When user enters valid credentials
  And user clicks login button
Then user is redirected to dashboard
```

### Example 2: Complex API Testing Scenario

**Before (JSON Stringify Format)**
```json
[{"content":"Given API endpoint is available\\nAnd authentication token is valid\\nWhen POST request is sent with valid payload\\nThen response status is 200\\nAnd response contains expected data\\nAnd database is updated"}]
```

**After (Formatted Gherkin)**
```gherkin
Given API endpoint is available
  And authentication token is valid
When POST request is sent with valid payload
Then response status is 200
  And response contains expected data
  And database is updated
```

### Example 3: Error Handling with But Keyword

**Before (JSON Stringify Format)**
```json
[{"content":"Given user has admin privileges\\nWhen user tries to delete a test run\\nBut the run has test results\\nThen system shows warning message\\nAnd deletion is prevented"}]
```

**After (Formatted Gherkin)**
```gherkin
Given user has admin privileges
When user tries to delete a test run
  But the run has test results
Then system shows warning message
  And deletion is prevented
```

## Related Documentation

- [API Documentation](API_DOCUMENTATION.md)
- [CRUD Operations Guide](CRUD_OPERATIONS_GUIDE.md)
- [User Guide: Gherkin Formatting](USER_GUIDE_GHERKIN.md)
