# ABO Tribe Automation

Appium/pytest suite for the ABO Tribe Android app. The suite currently covers
login, signup, location selection, nearby bars and the coin wallet / Coin
History flows.

## Setup

```powershell
python -m pip install -r requirements.txt
# Start Appium (default http://127.0.0.1:4723) and connect the test device.
```

Credentials and device-specific values are read from `.env`:

```text
TEST_MOBILE_NUMBER=...
TEST_OTP=...
INVALID_TEST_OTP=...
SIGNUP_PROFILE_DATA={"Full Name":"...","Email":"..."}
```

## Running

```powershell
python -m pytest tests/test_coins.py -q
python -m pytest tests/test_coins.py -m coin_history -q
python -m pytest tests/test_coins.py -m coin_credits -q
python -m pytest tests/test_coins.py -m coin_deductions -q
python -m pytest tests/test_coins.py -k coin_parser -q
```

The parser unit tests (`-k "coin_parser or invalid_coin_amounts"`) run without
a device or backend.

## Coin History tests

`tests/test_coins.py` maps to the coin requirements:

| Flow | Area |
| --- | --- |
| 1 | History display, balance, ordering, refresh, empty/error, privacy |
| 2.1-2.7 | Signup, check-in, referral, profile, game-win and multiple credits |
| 3.1-3.5 | Skip the Queue, Song Request, Shoutout, game entry and multiple deductions |
| 4-6 | Insufficient coins, not checked-in and disabled-feature negatives |
| 7-8 | Referral and profile-completion eligibility negatives |
| 9 | UI/backend balance and transaction integrity, retry safety |
| 10 | ABO Settings amount validation and historical-record stability |

### Backend validation (optional)

Backend checks are enabled when these are configured:

```text
ABO_API_BASE_URL=https://test.example.com
ABO_API_TOKEN=api_key:api_secret
# or
ABO_API_KEY=...
ABO_API_SECRET=...
```

The default endpoints are the Frappe resource API. Override them when the site
uses custom methods:

```text
ABO_SETTINGS_DOCTYPE=ABO Settings
ABO_COIN_HISTORY_DOCTYPE=Coin History
ABO_COIN_BALANCE_DOCTYPE=Coin Balance
ABO_CURRENT_USER_ENDPOINT=/api/method/frappe.auth.get_logged_user
ABO_COIN_HISTORY_ENDPOINT=/api/method/abo.api.get_coin_history
ABO_USER_BALANCE_ENDPOINT=/api/method/abo.api.get_coin_balance?user={user}
```

Reward doctypes can be renamed per environment with
`ABO_DOCTYPE_SIGNUP_BONUS`, `ABO_DOCTYPE_CHECKIN_BONUS`,
`ABO_DOCTYPE_REFERRAL_BONUS`, `ABO_DOCTYPE_PROFILE_COMPLETION_BONUS`,
`ABO_DOCTYPE_GAME_ENTRY`, `ABO_DOCTYPE_GAME_WIN_BONUS`,
`ABO_DOCTYPE_SKIP_THE_QUEUE`, `ABO_DOCTYPE_SONG_REQUEST` and
`ABO_DOCTYPE_SHOUTOUT_REQUEST`.

When the API is not configured, backend-only tests skip with a clear message.

### Flow-specific test data

```text
COIN_SIGNUP_MOBILE=...            # new user for signup/referral/profile flows
COIN_SIGNUP_OTP=...
COIN_REFERRAL_CODE=...
COIN_REFERRER_MOBILE=...          # user who owns the referral reward
COIN_REFERRER_OTP=...
COIN_BAR_NAME=...                 # bar used for check-in/feature flows
COIN_GAME_NAME=Dice
COIN_DISABLED_FEATURE=song_request
COIN_OTHER_USER_MOBILE=...
```

Amounts are read from ABO Settings through the API. For UI-only runs they can
be supplied explicitly, but they must match the active configuration:

```text
COIN_SIGNUP_BONUS=10
COIN_CHECKIN_BONUS=5
COIN_REFERRAL_REGISTRATION_BONUS=20
COIN_REFERRAL_BONUS=20
COIN_PROFILE_COMPLETE=10
COIN_GAME_ENTRY=1
COIN_GAME_WIN_BONUS=2
COIN_SKIP_THE_QUEUE=5
COIN_SONG_REQUEST=2
COIN_SHOUTOUT_REQUEST=2
```

Some negative flows (pending check-in, rejected check-in, insufficient coins,
disabled feature, empty history) depend on the state configured in the test bar
or backend. When the state cannot be produced the test skips rather than
reporting a false pass.
