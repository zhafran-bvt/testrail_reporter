# User Guide: BDD Scenarios Gherkin Formatting

## What's New? 🎉

The TestRail Reporter now automatically converts BDD scenarios from hard-to-read JSON format into beautiful, readable Gherkin format!

## Before vs After

### Before (What TestRail Stores)
```
[{"content":"Given user logged in\\nAnd user navigated to dashboard\\nWhen user clicks button\\nThen result is shown"}]
```
😵 Hard to read, difficult to edit

### After (What You See Now)
```gherkin
Given user logged in
  And user navigated to dashboard
When user clicks button
Then result is shown
```
😊 Easy to read, natural to edit

## How to Use

### Step 1: Open a Test Case for Editing

1. Go to **Management** view
2. Click on a **Test Plan**
3. Click on a **Test Run**
4. Click the **Edit** button on any test case

### Step 2: View Formatted BDD Scenarios

The **BDD Scenarios** field will automatically show your scenarios in readable Gherkin format with:
- ✅ Proper line breaks
- ✅ Indentation for And/But steps
- ✅ Clean, readable text

### Step 3: Edit Your Scenarios

You can now edit the BDD scenarios naturally:

```gherkin
Given user is authenticated
  And user has admin privileges
When user navigates to settings page
  And user changes configuration
Then changes are saved
  And confirmation message is shown
```

### Step 4: Save Changes

Click **Save Changes** - your formatted Gherkin will be saved to TestRail!

## Gherkin Format Guide

### Main Keywords (Left-Aligned)

- **Given** - Describes the initial context
- **When** - Describes an action or event
- **Then** - Describes the expected outcome

### Continuation Keywords (Indented)

- **And** - Adds another step of the same type
- **But** - Adds a contrasting step

### Example Structure

```gherkin
Given [initial context]
  And [additional context]
  And [more context]
When [action happens]
  And [another action]
Then [expected result]
  And [additional result]
  But [exception or contrast]
```

## Real-World Examples

### Example 1: Login Flow
```gherkin
Given user is on login page
When user enters email "test@example.com"
  And user enters password "SecurePass123"
  And user clicks login button
Then user is redirected to dashboard
  And welcome message is displayed
```

### Example 2: API Testing
```gherkin
Given API endpoint is available
  And authentication token is valid
When POST request is sent with payload
Then response status is 200
  And response contains user data
  And database is updated
```

### Example 3: Error Handling
```gherkin
Given user is not authenticated
When user tries to access protected resource
Then system returns 403 error
  And user is redirected to login page
  And error message is logged
```

## Tips for Writing Good BDD Scenarios

### ✅ Do's

1. **Be Specific**
   ```gherkin
   Given user has 5 items in cart
   ```
   Better than: `Given user has items`

2. **Use Business Language**
   ```gherkin
   When user completes checkout
   ```
   Better than: `When user clicks button ID 123`

3. **Focus on Behavior**
   ```gherkin
   Then order confirmation is sent
   ```
   Better than: `Then email function is called`

4. **Keep Steps Independent**
   Each scenario should be self-contained

### ❌ Don'ts

1. **Don't Mix Technical Details**
   ```gherkin
   # Bad
   Given database connection is established
   
   # Good
   Given user account exists
   ```

2. **Don't Make Steps Too Long**
   ```gherkin
   # Bad
   When user enters email and password and clicks login and waits for response
   
   # Good
   When user enters credentials
     And user clicks login button
   ```

3. **Don't Repeat Scenarios**
   Use data tables or scenario outlines instead

## Frequently Asked Questions

### Q: Will my old BDD scenarios still work?
**A:** Yes! The system automatically converts them to readable format when you open them for editing.

### Q: Do I need to do anything special?
**A:** No! The conversion happens automatically. Just open and edit as normal.

### Q: What if I paste JSON format directly?
**A:** The parser will detect and convert it automatically.

### Q: Can I still use plain text?
**A:** Yes! If your scenarios are already in plain text, they'll be formatted with proper indentation.

### Q: What happens when I save?
**A:** Your formatted Gherkin is saved to TestRail. You can edit it again anytime.

## Troubleshooting

### BDD Scenarios Look Wrong

**Problem:** Scenarios still show in JSON format

**Solution:**
1. Refresh the page (Ctrl+R or Cmd+R)
2. Clear browser cache
3. Check browser console for errors

### Indentation is Off

**Problem:** Steps aren't indented properly

**Solution:**
1. Check that steps start with Given/When/Then/And/But
2. The system auto-indents And/But steps
3. Main keywords (Given/When/Then) are always left-aligned

### Can't Edit Scenarios

**Problem:** BDD Scenarios field is not editable

**Solution:**
1. Make sure you clicked the Edit button
2. Check that you have edit permissions
3. Verify the test case has BDD scenarios data

## Need Help?

- 📖 See [GHERKIN_PARSING.md](GHERKIN_PARSING.md) for technical details
- 📝 See [GHERKIN_EXAMPLES.md](GHERKIN_EXAMPLES.md) for more examples
- 🧪 Use [test_gherkin_parsing.html](test_gherkin_parsing.html) to test the parser

## Feedback

Have suggestions for improving BDD scenarios? Let us know!

---

**Happy Testing! 🚀**
