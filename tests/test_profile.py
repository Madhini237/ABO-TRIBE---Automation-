r"""ABO Tribe - Profile Feature Manual Test Cases

This file intentionally holds the manual test-case document as a module
docstring. It is not executable automation. Add fixtures and test
functions below this docstring when automating the flow.

# ABO Tribe – Profile Feature Manual Test Cases

| Field | Value |
| --- | --- |
| Document ID | ABO-PROF-TC-001 |
| Feature | Profile Management |
| Application | ABO Tribe Android (`com.coredot.abo.abo_bar`) |
| Document version | 1.0 |
| Last updated | 18 Nov 2026 |
| Test approach | Manual, UI-only (backend data is validated indirectly through the UI and re-login) |
| Related flow | Profile Management Flow – positive, edit/view, module access, and negative scenarios |

---

## 1. Purpose and scope

This document covers the complete Profile feature flow:

- Profile entry after phone-number + OTP login/signup.
- Profile completion status, percentage, completed steps, and remaining steps.
- Completing mandatory profile details up to 100%.
- Viewing and editing profile information.
- Accessing ABO Coins, Bookings, Offers, and Saved Bars from Profile.
- Negative validation, persistence, network, server, and duplicate-completion scenarios.

**In scope:** UI behaviour, field validation, completion-state updates, persistence across navigation/re-login, and graceful error handling.

**Out of scope:** Backend/API contract testing, database integrity checks, performance, accessibility, localization, and security testing. The chosen approach is UI-only, so persistence is confirmed by reopening Profile and by logging out/in rather than by querying the backend.

---

## 2. Test environment and prerequisites

### 2.1 Environment

| Item | Requirement |
| --- | --- |
| Build | ABO Tribe Android test build containing the Profile feature |
| Device | Android device/emulator with SMS reception enabled |
| Network | Stable internet; ability to toggle airplane mode or set an unreachable HTTP proxy |
| Backend | Test environment with the ability to force a 5xx response for the profile-update call (for TC_PROF_018) |
| Accounts | One incomplete-profile account, one complete-profile account (or backend reset capability), and one fresh mobile number with SMS access |
| App state | Signed-in session for most cases; signed-out state for the authentication-entry cases |

### 2.2 Preconditions for execution

1. The app is installed and launches without crashing.
2. The tester can receive the OTP on the device (SMS notification or message inbox).
3. Test accounts and numbers from the test-data section are available.
4. The device clock, date format, and locale match the intended test configuration.
5. Device state (airplane mode, proxy, permissions) is restored after each resilience test.

---

## 3. Test data and configuration

All test data is environment-driven and has safe defaults. Profile field labels must match the labels visible in the app; keys in the JSON values are the visible labels.

| Variable | Default / example | Used by | Notes |
| --- | --- | --- | --- |
| `TEST_MOBILE_NUMBER` | Existing signed-in test account | TC_PROF_001, 003–020 | Must have a profile; can be incomplete or complete depending on the case |
| `SIGNUP_MOBILE_NUMBER` | Fresh 10-digit number with SMS access | TC_PROF_002 | Must differ from existing accounts |
| `OTP` | Read from the device SMS | TC_PROF_001, 002 | Do not use a fixed/stale OTP; wait up to `OTP_WAIT_TIMEOUT` (default 120 s) |
| `SIGNUP_PROFILE_DATA` | `{"Full Name":"Profile Test User","Email":"profile.test@example.com","Date of Birth":"1995-05-15","Gender":"Male"}` | Signup and completion cases | Existing suite variable; keys are visible field labels |
| `PROFILE_VALID_DATA` | Falls back to `SIGNUP_PROFILE_DATA`, then the defaults above | TC_PROF_004–007, 009 | Use a different value per step when needed |
| `PROFILE_EDIT_DATA` | `{"Full Name":"Profile Test User Edited","Email":"profile.edited@example.com"}` | TC_PROF_009 | Must contain valid values |
| `PROFILE_REQUIRED_FIELD` | `Full Name` | TC_PROF_015 | A field that the app marks mandatory |
| `PROFILE_TOTAL_STEPS` | Empty → read the total from the Profile screen | TC_PROF_005–007 | Set only when the app's total is known |
| `PROFILE_EXPECTED_PERCENTAGES` | Empty → derive from completed/total steps | TC_PROF_005, 006 | Optional JSON list, e.g. `[25,50,75,100]` |
| `PROFILE_PERCENT_TOLERANCE` | `1` | TC_PROF_003, 005–007 | Allowed rounding difference in percentage points |
| `PROFILE_STEPS` | Empty → use the steps shown in the UI | TC_PROF_005 | Optional JSON map of step name → field labels |
| `PROFILE_NO_CHANGE_MESSAGE` | `No Changes Detected` | TC_PROF_016 | Accept an equivalent message or remaining on the page with no save |
| `PROFILE_NETWORK_ERROR_MESSAGE` | `Network Error` | TC_PROF_017 | Accept equivalents such as "No internet connection" or "Please check your connection" |
| `PROFILE_SERVER_ERROR_MESSAGE` | `Something went wrong` | TC_PROF_018 | Accept equivalents such as "Server error", "Unable to update profile", or "Please try again later" |
| `PROFILE_API_FAILURE_PROXY` | `127.0.0.1:1` | TC_PROF_017, 018 | Unreachable proxy that keeps the device online while backend calls fail |
| `PROFILE_RESTORE_DEVICE_STATE` | `true` | TC_PROF_017, 018 | Restore airplane mode/proxy after the test |
| `PROFILE_RELAUNCH_WAIT` | `15` seconds | Persistence checks | Time allowed after relaunch/re-login |

### 3.1 Invalid-value variants for TC_PROF_014

Use each variant independently and restore the valid value between attempts.

| Field | Variant examples | Reason |
| --- | --- | --- |
| Email | `invalid.email`, `user@`, `@example.com`, `user name@example.com` | Invalid format / spaces |
| Name | `<>`, `Test@#$`, emoji, single character, value beyond the maximum length | Unsupported characters or length limits |
| Date of birth | Future date, `31/02/1995`, age below the app's minimum | Invalid or ineligible date |
| Phone number (if editable) | Fewer than 10 digits, alphabetic characters, leading/trailing spaces | Invalid format |
| Email/phone | A value already used by another account (if uniqueness is enforced) | Duplicate value |

### 3.2 Account-state management

- **Incomplete profile:** Sign up with a fresh number and skip the optional profile setup, or reset the profile completion state through the backend test tools.
- **Partially complete profile:** Complete one or more steps and leave at least one mandatory step untouched.
- **Complete profile:** Complete all mandatory steps or use a preconfigured 100% account.
- Do not reuse the same fresh signup number across runs; it will no longer represent a new user.

---

## 4. Conventions

### 4.1 Priority

| Priority | Meaning |
| --- | --- |
| P1 | Critical happy path or data-integrity scenario; must pass before release |
| P2 | Important validation, module, or resilience scenario |
| P3 | Low-risk edge case or cosmetic check |

### 4.2 Execution status

| Status | Meaning |
| --- | --- |
| Pass | Actual result matches all expected results |
| Fail | Any expected result is not met; raise a defect |
| Blocked | Environment, data, or backend control prevents execution |
| Not Run | Not executed in this cycle |

### 4.3 Expected-result conventions

- "Step completed" means the app saved the values and reflected them in the completion widget.
- The percentage is app-defined; verify **consistency** with the completed-step count rather than a hardcoded weight. With equally weighted steps and `N` total steps, completing `k` steps should show approximately `round(k / N × 100)%` (within `PROFILE_PERCENT_TOLERANCE`).
- Record the exact UI copy (for example "50% Completed – 2 Steps Completed") in the execution notes; copy may legitimately differ from the examples in this document.
- Re-opening Profile or logging out/in confirms UI persistence. Backend/API verification is intentionally excluded.

---

## 5. Test case summary

| ID | Title | Type | Priority | Requirement area |
| --- | --- | --- | --- | --- |
| TC_PROF_001 | Profile entry after existing-user phone + OTP login | Positive | P1 | Authentication entry |
| TC_PROF_002 | Profile entry after new-user signup with phone + OTP | Positive | P1 | Authentication entry |
| TC_PROF_003 | Profile page displays completion status and sections | Positive | P1 | Profile dashboard |
| TC_PROF_004 | Open Complete/Edit Profile from an incomplete profile | Positive | P1 | Completion flow |
| TC_PROF_005 | Completion percentage and step count update after each step | Positive | P1 | Completion flow |
| TC_PROF_006 | Completion status shows percentage, completed and remaining steps | Positive | P1 | Completion status |
| TC_PROF_007 | All mandatory details completed → 100% and persistence | Positive | P1 | Completion flow |
| TC_PROF_008 | View saved profile information | Positive | P1 | View Profile |
| TC_PROF_009 | Edit profile and save updated information | Positive | P1 | Edit Profile |
| TC_PROF_010 | View ABO Coins balance and details/history | Positive | P2 | ABO Coins |
| TC_PROF_011 | View table and event bookings with status | Positive | P2 | Bookings |
| TC_PROF_012 | View available, claimed, and past offers | Positive | P2 | Offers |
| TC_PROF_013 | View all saved/favourite bars | Positive | P2 | Saved Bars |
| TC_PROF_014 | Invalid profile details are rejected and not saved | Negative | P1 | Validation |
| TC_PROF_015 | Mandatory field missing blocks the update | Negative | P1 | Validation |
| TC_PROF_016 | Save/Update with no changes | Negative | P2 | Edit Profile |
| TC_PROF_017 | Network failure during save and successful retry | Negative | P2 | Resilience |
| TC_PROF_018 | Server error during save | Negative | P2 | Resilience |
| TC_PROF_019 | Partially completed profile is retained after navigating away | Negative | P1 | Persistence |
| TC_PROF_020 | Duplicate step completion does not increase percentage | Negative | P1 | Completion integrity |

**Execution tracking**

| ID | Status | Actual result / notes | Defect ID | Tester | Date |
| --- | --- | --- | --- | --- | --- |
| TC_PROF_001 |  |  |  |  |  |
| TC_PROF_002 |  |  |  |  |  |
| TC_PROF_003 |  |  |  |  |  |
| TC_PROF_004 |  |  |  |  |  |
| TC_PROF_005 |  |  |  |  |  |
| TC_PROF_006 |  |  |  |  |  |
| TC_PROF_007 |  |  |  |  |  |
| TC_PROF_008 |  |  |  |  |  |
| TC_PROF_009 |  |  |  |  |  |
| TC_PROF_010 |  |  |  |  |  |
| TC_PROF_011 |  |  |  |  |  |
| TC_PROF_012 |  |  |  |  |  |
| TC_PROF_013 |  |  |  |  |  |
| TC_PROF_014 |  |  |  |  |  |
| TC_PROF_015 |  |  |  |  |  |
| TC_PROF_016 |  |  |  |  |  |
| TC_PROF_017 |  |  |  |  |  |
| TC_PROF_018 |  |  |  |  |  |
| TC_PROF_019 |  |  |  |  |  |
| TC_PROF_020 |  |  |  |  |  |

---

## 6. Detailed test cases

### TC_PROF_001 – Profile entry after existing-user phone + OTP login

| Attribute | Value |
| --- | --- |
| Type | Positive |
| Priority | P1 |
| Category | Functional / Authentication entry |
| Preconditions | App is installed and signed out; `TEST_MOBILE_NUMBER` is an existing account that can receive SMS |
| Test data | `TEST_MOBILE_NUMBER`, live OTP, `OTP_WAIT_TIMEOUT` (default 120 s) |

**Steps**

1. Launch the ABO Tribe app.
2. Enter `TEST_MOBILE_NUMBER` on the phone-number screen and tap **Login/Continue**.
3. Wait for the OTP SMS and enter the received OTP.
4. Tap **Verify** (or wait for auto-verification).
5. Observe the homepage/dashboard.
6. Locate the **Profile** icon and tap it.
7. Observe the Profile page.

**Expected results**

1. The app opens on the phone-number entry screen without an error.
2. The OTP verification screen opens; no validation error is shown.
3. The OTP field accepts the code.
4. OTP is accepted; no "invalid OTP" feedback is shown.
5. The homepage opens successfully and is fully loaded.
6. A visible, enabled Profile icon is present on the homepage/navigation bar.
7. The Profile page opens without a crash and shows the signed-in user's profile and completion status.

**Postcondition:** The tester is on the Profile page for the signed-in test account.

---

### TC_PROF_002 – Profile entry after new-user signup with phone + OTP

| Attribute | Value |
| --- | --- |
| Type | Positive |
| Priority | P1 |
| Category | Functional / Authentication entry |
| Preconditions | App is signed out; a fresh mobile number with SMS access is available |
| Test data | `SIGNUP_MOBILE_NUMBER`, live OTP, optional `SIGNUP_PROFILE_DATA` |

**Steps**

1. Launch the app and open the phone-number/authentication screen.
2. Enter `SIGNUP_MOBILE_NUMBER` and request the OTP.
3. Enter the received OTP and verify.
4. If the app shows the optional signup profile form, complete or skip it as configured.
5. If a signup/welcome bonus dialog appears, dismiss or continue as prompted.
6. Wait for the homepage/dashboard.
7. Tap the **Profile** icon.

**Expected results**

1. Registration/signup completes successfully with the new number.
2. OTP verification succeeds without an error.
3. Any signup profile step is handled according to the configured path.
4. The bonus dialog (when present) is dismissed and does not block navigation.
5. The homepage opens successfully.
6. The Profile icon is visible and enabled.
7. The Profile page opens and reflects the new account's state (incomplete unless the signup form was completed).

**Postcondition:** A new account exists and is signed in; Profile is reachable.

---

### TC_PROF_003 – Profile page displays completion status and sections

| Attribute | Value |
| --- | --- |
| Type | Positive |
| Priority | P1 |
| Category | UI / Functional |
| Preconditions | Signed in; Profile page reachable; one incomplete and one complete account available |
| Test data | `PROFILE_TOTAL_STEPS` (optional), `PROFILE_PERCENT_TOLERANCE` |

**Steps**

1. Open Profile from the homepage.
2. Observe the user information area (name/phone/avatar or equivalent).
3. Observe the completion status area.
4. Record the displayed percentage, completed steps, and remaining steps.
5. Observe the ABO Coins, Bookings, Offers, and Saved Bars entries.
6. Tap each entry once to confirm it is interactive, then return to Profile.
7. Repeat steps 1–5 with the complete-profile account.

**Expected results**

1. The Profile page loads without an error, blank screen, or endless spinner.
2. User information is displayed.
3. A completion percentage between 0% and 100% is shown with a `%` indicator and/or progress bar.
4. Completed-step and remaining-step counts are shown and are internally consistent:
   - Completed + remaining = total steps.
   - Percentage is consistent with the completed-step count (within tolerance).
5. ABO Coins, Bookings, Offers, and Saved Bars are all visible.
6. Each entry opens its respective screen or section; returning to Profile succeeds.
7. For the complete account, the status shows 100% and all steps completed.

**Notes:** If the app hides "remaining steps" at 100%, record this as acceptable provided the completed count equals the total.

---

### TC_PROF_004 – Open Complete/Edit Profile from an incomplete profile

| Attribute | Value |
| --- | --- |
| Type | Positive |
| Priority | P1 |
| Category | Functional / Completion flow |
| Preconditions | Signed in with an incomplete profile; Profile page open |
| Test data | `PROFILE_VALID_DATA` |

**Steps**

1. On the Profile page, tap **Complete Profile** or **Edit Profile**.
2. Observe the profile form/step list.
3. Check whether previously saved values are prefilled.
4. Check the available actions (Save/Update/Continue/Back).

**Expected results**

1. The editable profile form or step-by-step completion screen opens.
2. All mandatory steps/fields required for completion are visible or listed.
3. Previously saved values are prefilled and editable.
4. A Save/Update/Continue action is available; the screen does not crash or show a blank form.

---

### TC_PROF_005 – Completion percentage and step count update after each step

| Attribute | Value |
| --- | --- |
| Type | Positive |
| Priority | P1 |
| Category | Functional / Completion flow |
| Preconditions | Incomplete profile; total mandatory step count known (`N`) or visible in the UI; valid data available |
| Test data | `PROFILE_VALID_DATA`, `PROFILE_STEPS` (optional), `PROFILE_TOTAL_STEPS`, `PROFILE_PERCENT_TOLERANCE` |

**Steps**

1. Open Profile and record the starting percentage and completed-step count.
2. Open the first incomplete mandatory step.
3. Enter valid values and save.
4. Return to the Profile page.
5. Record the new percentage, completed-step count, and remaining-step count.
6. Repeat steps 2–5 for each remaining mandatory step, one step at a time.
7. After each save, navigate away from Profile and reopen it.

**Expected results**

1. The starting state matches the account's actual completion state.
2. Only the selected step is open for editing.
3. Valid values save successfully with a success confirmation (if the app provides one).
4. The Profile page refreshes with a higher percentage.
5. After completing the `k`-th step:
   - Completed steps = `k` (increments by exactly 1).
   - Remaining steps = `N − k`.
   - Percentage matches `round(k / N × 100)%` within `PROFILE_PERCENT_TOLERANCE`, unless the app uses documented unequal weights.
   - The percentage never decreases and never jumps by more than one step's weight.
6. The updated state is unchanged after navigating away and back.

**Example with 4 equally weighted steps:** 25% / 1 step → 50% / 2 steps → 75% / 3 steps → 100% / 4 steps.

**Negative sub-check:** Saving a step with empty mandatory fields must not increase the percentage (see TC_PROF_015).

---

### TC_PROF_006 – Completion status shows percentage, completed and remaining steps

| Attribute | Value |
| --- | --- |
| Type | Positive |
| Priority | P1 |
| Category | UI / Completion status |
| Preconditions | Accounts/states available at 0%, partial (for example 50%), and 100% completion |
| Test data | `PROFILE_EXPECTED_PERCENTAGES` (optional), `PROFILE_PERCENT_TOLERANCE` |

**Steps**

1. Open Profile for the 0% state and record the status text.
2. Open Profile for the partial state and record the status text.
3. Open Profile for the 100% state and record the status text.
4. Compare the displayed percentage with the completed/remaining counts in each state.
5. If a progress bar exists, compare its fill level with the percentage.

**Expected results**

1. The 0% state shows 0% and zero completed steps (or the app's documented initial state).
2. The partial state shows the expected percentage and step counts, for example "50% Completed – 2 Steps Completed".
3. The 100% state shows 100% and all steps completed; remaining steps are 0 or hidden.
4. The percentage and step counts never contradict each other in any state.
5. The progress bar, when present, matches the numeric percentage within tolerance.

**Notes:** Exact copy is app-defined; verify semantics and consistency rather than literal wording.

---

### TC_PROF_007 – All mandatory details completed → 100% and persistence

| Attribute | Value |
| --- | --- |
| Type | Positive |
| Priority | P1 |
| Category | Functional / Persistence |
| Preconditions | Incomplete profile; valid data for every mandatory step; ability to log out and back in |
| Test data | `PROFILE_VALID_DATA`, `PROFILE_RELAUNCH_WAIT` |

**Steps**

1. Open Profile and note the total number of mandatory steps.
2. Complete every mandatory step with valid values, saving after each step.
3. Return to the Profile page.
4. Verify the completion status.
5. Confirm ABO Coins, Bookings, Offers, and Saved Bars are still visible/accessible.
6. Force-close and relaunch the app, then reopen Profile.
7. Log out and log in again with the same account, then reopen Profile.
8. Open Edit Profile and verify the saved values.

**Expected results**

1. Every mandatory step saves successfully.
2. The completion status reaches 100% and the completed-step count equals the total.
3. Remaining steps are 0 or no longer displayed.
4. All four sections remain visible and accessible.
5. After relaunch, Profile still shows 100% and the saved data.
6. After logout/login, Profile still shows 100% and the saved data (confirming server-side persistence).
7. Edit Profile shows the same values that were saved; no field resets or duplicates.

**Postcondition:** The account remains at 100% completion with all mandatory data saved.

---

### TC_PROF_008 – View saved profile information

| Attribute | Value |
| --- | --- |
| Type | Positive |
| Priority | P1 |
| Category | Functional / View Profile |
| Preconditions | Signed in with a saved profile (partial or complete); Profile page reachable |
| Test data | The account's known saved values |

**Steps**

1. Tap the Profile icon from the homepage.
2. Observe the user information and completion status.
3. Scroll through the Profile page.
4. Verify ABO Coins, Bookings, Offers, and Saved Bars entries.
5. Tap Back or Home and reopen Profile.

**Expected results**

1. The Profile page opens successfully.
2. The displayed user information matches the saved profile data.
3. Completion percentage and step counts are displayed.
4. ABO Coins, Bookings, Offers, and Saved Bars are all displayed.
5. Reopening Profile shows the same information with no reset or flicker to stale values.

---

### TC_PROF_009 – Edit profile and save updated information

| Attribute | Value |
| --- | --- |
| Type | Positive |
| Priority | P1 |
| Category | Functional / Edit Profile |
| Preconditions | Signed in; Profile page reachable; valid alternative data available |
| Test data | `PROFILE_EDIT_DATA`, `PROFILE_RELAUNCH_WAIT` |

**Steps**

1. Tap **Edit Profile**.
2. Verify the editable fields are displayed with current values.
3. Modify one or more valid fields using `PROFILE_EDIT_DATA`.
4. Tap **Save/Update**.
5. Observe validation and confirmation feedback.
6. Verify the updated values on the Profile page.
7. Relaunch the app or log out/in and reopen Profile.
8. Open Edit Profile again.

**Expected results**

1. Edit mode opens with the current values prefilled.
2. Editable fields are displayed and accept input.
3. Valid changes are accepted.
4. Save/Update completes without an error.
5. A success confirmation is shown (if the app provides one).
6. The Profile page displays the updated information.
7. The changes persist after relaunch/re-login.
8. Edit mode shows the updated values; no stale or duplicated data is displayed.

**Note:** For a completed profile, the percentage should remain 100%; for a partial profile, it should be recalculated only if the edit completes a previously incomplete mandatory step.

---

### TC_PROF_010 – View ABO Coins balance and details/history

| Attribute | Value |
| --- | --- |
| Type | Positive |
| Priority | P2 |
| Category | Functional / ABO Coins |
| Preconditions | Signed in; Profile page open; account may have zero or more coin transactions |
| Test data | None (use the signed-in account) |

**Steps**

1. Tap **ABO Coins** from the Profile page.
2. Observe the coin balance and coin-related details/history.
3. Scroll through the history if present.
4. Tap Back and reopen ABO Coins.
5. Repeat with an account that has no coin history, if available.

**Expected results**

1. The ABO Coins screen opens without an error.
2. The coin balance is displayed as a valid numeric value and is not negative.
3. Coin-related details/history are displayed (transaction type, amount, date, and balance where applicable).
4. The same balance is shown after returning and reopening.
5. An empty-history account shows a clear empty state rather than a blank screen or crash.
6. Back navigation returns to Profile with its state intact.

---

### TC_PROF_011 – View table and event bookings with status

| Attribute | Value |
| --- | --- |
| Type | Positive |
| Priority | P2 |
| Category | Functional / Bookings |
| Preconditions | Signed in; Profile page open; account with table and/or event bookings, or a no-booking account for the empty state |
| Test data | The signed-in account's known bookings |

**Steps**

1. Tap **Bookings** from Profile.
2. Observe the list of table bookings.
3. Observe the list of event bookings (or the relevant tab/section).
4. Check the details shown for each booking.
5. Check the status shown for each booking.
6. Tap a booking, if the app supports detail navigation.
7. Return to Profile.

**Expected results**

1. The Bookings screen opens without an error.
2. Table bookings are displayed.
3. Event bookings are displayed (or a clear empty state is shown for that category).
4. Each booking shows the expected identifying details (bar/event name, date/time, and guest/table information where applicable).
5. Each booking shows a valid status such as Pending, Confirmed, Cancelled, Completed, or Rejected, consistent with the booking's actual state.
6. Booking detail navigation works when supported; no crash or stale data.
7. Back navigation returns to Profile with its state intact.
8. A no-booking account shows a clear empty state.

---

### TC_PROF_012 – View available, claimed, and past offers

| Attribute | Value |
| --- | --- |
| Type | Positive |
| Priority | P2 |
| Category | Functional / Offers |
| Preconditions | Signed in; Profile page open; account with available and claimed offers, or a no-offer account for the empty state |
| Test data | The signed-in account's known offers |

**Steps**

1. Tap **Offers** from Profile.
2. Observe the available offers.
3. Observe claimed offers or offer history.
4. Check the offer details (title, description, validity, terms where applicable).
5. Check the status of each offer (available/claimed/expired).
6. Return to Profile and reopen Offers.

**Expected results**

1. The Offers screen opens without an error.
2. Available offers are displayed.
3. Claimed offers or offer history are displayed in the appropriate section/tab.
4. Each offer shows its expected details.
5. Offer status is consistent with the account's claim history (claimed offers do not appear as unclaimed).
6. Reopening the screen shows the same data; no duplicates or reset.
7. A no-offer account shows a clear empty state.
8. Back navigation returns to Profile.

---

### TC_PROF_013 – View all saved/favourite bars

| Attribute | Value |
| --- | --- |
| Type | Positive |
| Priority | P2 |
| Category | Functional / Saved Bars |
| Preconditions | Signed in; Profile page open; account with saved bars, or a no-saved-bar account for the empty state |
| Test data | The signed-in account's known saved bars |

**Steps**

1. Tap **Saved Bars** from Profile.
2. Observe the list of saved/favourite bars.
3. Compare the list with the bars the account previously saved.
4. Tap a saved bar, if the app supports detail navigation.
5. Return to the Saved Bars list and then to Profile.

**Expected results**

1. The Saved Bars screen opens without an error.
2. All bars marked as favourite/saved by the account are displayed.
3. Bars that were not saved are not shown.
4. Each saved bar shows its expected identifying information.
5. Tapping a bar opens its details when supported; no crash.
6. Back navigation returns to the Saved Bars list and then to Profile with state intact.
7. A no-saved-bar account shows a clear empty state.

---

### TC_PROF_014 – Invalid profile details are rejected and not saved

| Attribute | Value |
| --- | --- |
| Type | Negative |
| Priority | P1 |
| Category | Validation |
| Preconditions | Signed in; Profile page reachable; edit/completion form available; account has a known valid state |
| Test data | The invalid variants in section 3.1; `PROFILE_VALID_DATA` for restoration |

**Steps**

1. Record the current completion percentage and completed-step count.
2. Open **Edit Profile** (or the relevant completion step).
3. Replace one field with an invalid value from section 3.1.
4. Tap **Save/Update**.
5. Observe the validation feedback.
6. Reopen Profile and the edited step to check whether the invalid value was saved.
7. Restore the valid value and repeat steps 2–6 for each invalid variant.

**Expected results**

1. The current percentage and step count are recorded before each attempt.
2. The invalid value can be entered (so validation is exercised on save).
3. The app displays an appropriate field-level or form-level validation message.
4. The save is blocked; no success confirmation is shown.
5. The invalid value is not persisted (reopening shows the previous valid value).
6. The profile completion percentage and completed-step count remain unchanged.
7. Previously saved valid data is preserved.
8. The app remains responsive and does not crash for any variant.

**Notes:** If the field restricts input (for example, a date picker or numeric keyboard) such that a variant cannot be entered, record the constraint and use the nearest invalid variant that can be entered.

---

### TC_PROF_015 – Mandatory field missing blocks the update

| Attribute | Value |
| --- | --- |
| Type | Negative |
| Priority | P1 |
| Category | Validation |
| Preconditions | Signed in; edit/completion form available; at least one mandatory field is populated |
| Test data | `PROFILE_REQUIRED_FIELD` (default `Full Name`) |

**Steps**

1. Record the current completion percentage and completed-step count.
2. Open **Edit Profile** or the relevant completion step.
3. Clear the mandatory field identified by `PROFILE_REQUIRED_FIELD`.
4. Tap **Save/Update**.
5. Observe the validation feedback.
6. Also test with a whitespace-only value for the same field.
7. Cancel/close the form and reopen Profile.

**Expected results**

1. The current percentage and step count are recorded.
2. The mandatory field is empty.
3. An appropriate "required field" validation message is displayed for the field.
4. The profile update is not completed; no success confirmation is shown.
5. The profile completion percentage is not increased.
6. Whitespace-only input is also rejected as missing.
7. Reopening Profile shows the previously saved data and the unchanged completion state.

---

### TC_PROF_016 – Save/Update with no changes

| Attribute | Value |
| --- | --- |
| Type | Negative |
| Priority | P2 |
| Category | Edit Profile |
| Preconditions | Signed in; profile has saved data; edit/completion form available |
| Test data | `PROFILE_NO_CHANGE_MESSAGE` (default `No Changes Detected`) |

**Steps**

1. Record the current profile values, completion percentage, and completed-step count.
2. Open **Edit Profile**.
3. Without modifying any field, tap **Save/Update**.
4. Observe the feedback and page state.
5. Tap **Save/Update** again without changes.
6. Reopen Profile and the edit form.

**Expected results**

1. The current state is recorded.
2. Edit mode opens with the existing values.
3. The app displays "No Changes Detected" (or an equivalent message) or remains on the page without saving.
4. No duplicate update confirmation is shown; existing profile information remains unchanged.
5. Repeated Save/Update taps do not create duplicates or errors.
6. Reopening shows the same values and completion state.

**Notes:** The flow explicitly allows remaining on the page as an alternative to a "No Changes Detected" message.

---

### TC_PROF_017 – Network failure during save and successful retry

| Attribute | Value |
| --- | --- |
| Type | Negative |
| Priority | P2 |
| Category | Resilience / Network |
| Preconditions | Signed in; profile edit form available; tester can toggle airplane mode or set an unreachable HTTP proxy; device state can be restored |
| Test data | `PROFILE_VALID_DATA` or `PROFILE_EDIT_DATA`; `PROFILE_NETWORK_ERROR_MESSAGE`; `PROFILE_API_FAILURE_PROXY` (optional) |

**Steps**

1. Open **Edit Profile** and enter valid changes.
2. Record the current completion percentage and step count.
3. Enable airplane mode (or set the unreachable proxy) so the device is offline for the app.
4. Tap **Save/Update**.
5. Observe the error feedback and wait for any loading indicator to stop.
6. Disable airplane mode / clear the proxy and confirm connectivity is restored.
7. Tap **Save/Update** again (or reopen the form and retry).
8. Verify the resulting profile state and completion percentage.

**Expected results**

1. Valid changes are entered before the failure.
2. The current percentage and step count are recorded.
3. The app loses connectivity as intended.
4. The app displays a network error message (or an equivalent message such as "No internet connection").
5. The profile update fails; the completion percentage and step count remain unchanged.
6. The loading indicator stops; the app does not hang or crash.
7. After connectivity is restored, retry succeeds with a success confirmation.
8. The final profile data is correct, with no duplicate or partial updates.
9. Device connectivity settings are restored after the test.

---

### TC_PROF_018 – Server error during save

| Attribute | Value |
| --- | --- |
| Type | Negative |
| Priority | P2 |
| Category | Resilience / Server error |
| Preconditions | Signed in; profile edit form available; test backend can return a 5xx for the profile-update request, or an unreachable proxy can be used |
| Test data | `PROFILE_VALID_DATA` or `PROFILE_EDIT_DATA`; `PROFILE_SERVER_ERROR_MESSAGE`; test-environment error toggle/proxy |

**Steps**

1. Configure the test environment to return a server error for the profile-update request.
2. Open **Edit Profile** and enter valid changes.
3. Record the current completion percentage and step count.
4. Tap **Save/Update**.
5. Observe the error feedback.
6. Restore the backend to normal operation.
7. Retry the save and verify the profile state.

**Expected results**

1. The server-error condition is active before submission.
2. Valid changes are entered.
3. The current percentage and step count are recorded.
4. The app displays an appropriate error message; it does not claim success.
5. The profile information and completion percentage remain unchanged.
6. The app remains responsive; no crash or data corruption.
7. After the backend is restored, retry succeeds and the correct data is displayed.
8. If the environment cannot force a server error, mark this case **Blocked**, not Pass.

---

### TC_PROF_019 – Partially completed profile is retained after navigating away

| Attribute | Value |
| --- | --- |
| Type | Negative |
| Priority | P1 |
| Category | Persistence / Incomplete profile |
| Preconditions | Signed in with an incomplete profile (at least one mandatory step remaining); valid data available |
| Test data | `PROFILE_VALID_DATA`, `PROFILE_RELAUNCH_WAIT` |

**Steps**

1. Open Profile and record the starting percentage, completed steps, and remaining steps.
2. Complete one or more mandatory steps and save them.
3. Record the new percentage and step counts.
4. Navigate away from Profile (Back/Home) without completing the remaining steps.
5. Reopen Profile.
6. Relaunch the app (or log out/in) and reopen Profile.
7. Open the completed step(s) again.
8. Open a remaining mandatory step and then close it without saving.

**Expected results**

1. The starting state is recorded.
2. The selected steps save successfully.
3. The percentage and completed-step count increase as expected.
4. Navigating away is allowed; no forced completion is required.
5. On revisit, the same percentage and completed-step count are displayed.
6. The values persist after relaunch/re-login.
7. Completed steps show the saved values.
8. The remaining step stays incomplete and the percentage does not increase without a save.

**Postcondition:** The profile remains partially completed with all successfully saved data retained.

---

### TC_PROF_020 – Duplicate step completion does not increase percentage

| Attribute | Value |
| --- | --- |
| Type | Negative |
| Priority | P1 |
| Category | Completion integrity / Idempotency |
| Preconditions | Signed in with at least one completed profile step; Profile page reachable |
| Test data | The exact values already saved for the completed step |

**Steps**

1. Open Profile and record the percentage and completed-step count.
2. Open an already completed step.
3. Re-enter or keep the same information and tap **Save/Update**.
4. Return to Profile and record the percentage and step count.
5. Repeat steps 2–4 a second time.
6. If the app shows step history or completion records, check for duplicates.
7. Relaunch the app and reopen Profile.

**Expected results**

1. The current percentage and step count are recorded.
2. The completed step opens with its saved values.
3. Saving the same information succeeds or shows "No Changes Detected"; no error occurs.
4. The profile completion percentage does not increase.
5. The completed-step count does not increase.
6. No duplicate completion entry/record is created.
7. After relaunch, the percentage and step count remain unchanged.

---

## 7. Traceability matrix

| Flow requirement | Test cases |
| --- | --- |
| Login/signup with phone + OTP → homepage → Profile icon visible → Profile opens | TC_PROF_001, TC_PROF_002 |
| Profile completion status/percentage and completed steps displayed | TC_PROF_003, TC_PROF_006 |
| Complete/Edit Profile entry from an incomplete profile | TC_PROF_004 |
| Percentage and step count update after each completed step | TC_PROF_005, TC_PROF_006 |
| Show completed and remaining steps | TC_PROF_005, TC_PROF_006 |
| Complete all mandatory details → 100% completion | TC_PROF_007 |
| Updated profile saved and persisted | TC_PROF_007, TC_PROF_009 |
| View profile information and sections | TC_PROF_003, TC_PROF_008 |
| Edit profile and save valid changes | TC_PROF_009 |
| View ABO Coins | TC_PROF_010 |
| View Bookings (table and event) with status | TC_PROF_011 |
| View Offers (available/claimed/history) | TC_PROF_012 |
| View Saved Bars | TC_PROF_013 |
| Invalid profile details rejected, percentage unchanged | TC_PROF_014 |
| Required field missing blocks update | TC_PROF_015 |
| No changes made on Save/Update | TC_PROF_016 |
| Network failure, no update, retry after restoration | TC_PROF_017 |
| Server error, no update, retry | TC_PROF_018 |
| Incomplete profile retained after navigating away | TC_PROF_019 |
| Duplicate step completion does not increase percentage | TC_PROF_020 |

---

## 8. Assumptions and open points

1. **App-defined completion model:** The mandatory steps, their weights, and the exact percentage calculation are app-defined. The cases verify consistency with the displayed step count rather than hardcoding a formula. If the app uses unequal weights, record the weights and update `PROFILE_EXPECTED_PERCENTAGES`.
2. **UI copy:** Messages such as "No Changes Detected", "Network Error", and "100% Completed" may differ in the build. Record the exact copy; equivalents are acceptable where the meaning is the same.
3. **Optional profile setup:** New users may be allowed to skip profile setup during signup. TC_PROF_002 supports both the completed and skipped variants.
4. **Persistence:** Because this is a UI-only suite, "saved in the backend" is verified through re-login/re-launch. If direct API/database validation is later required, add separate backend test cases and endpoint details.
5. **Server-error control:** TC_PROF_018 depends on a test-environment toggle or proxy. If neither is available, the case is **Blocked**, not passed.
6. **Device restoration:** Any test that changes airplane mode, proxy, or other device settings must restore them in a `finally` block/after-test step.
7. **Test-account uniqueness:** Use a fresh number only for new-signup cases; do not consume it for repeat runs. Use dedicated incomplete/partial/complete accounts for completion tests.
8. **Data cleanup:** Profile data created during testing should be reset or the test accounts retired according to the QA data-management process.

---

## 9. Exit criteria

- All P1 cases pass.
- No open S1/S2 defects related to profile completion, data loss, or incorrect persistence.
- P2 failures are reviewed, documented, and either fixed or formally accepted.
- Any Blocked cases have a documented environmental reason and a follow-up plan.
- Device network/proxy settings are restored.
"""
