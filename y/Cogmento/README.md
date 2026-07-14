# Cogmento yPAD – FoXYiZ

yPAD (Plans, Actions, Designs) to test **Cogmento CRM** (https://ui.cogmento.com) using the FoXYiZ engine.

## Element identification – no commas in CSV

- **Locators** are defined in `y3Designs.csv` using **CSS only** (`css=...`).
- **No commas** are used inside any CSV cell for element identification, so parsing stays simple and robust.
- Alternatives: use semicolon in Input for value;locator (e.g. `login_email;login_email_locator`). Multiple selectors are not combined with commas; each design row has one CSS selector.

## Files

| File | Purpose |
|------|--------|
| `y1Plans.csv` | Test plans (Open Browser, Login, Navigation, Create Contact, Logout). |
| `y2Actions.csv` | Steps per plan (xUI: xOpenBrowser, xNavigate, xType, xClick, xWaitFor). |
| `y3Designs.csv` | Data and **CSS locators** (no commas); credentials and URLs go in D1/D2/D3. |

## Setup

1. In `y3Designs.csv`, set **login_email** and **login_password** (D1/D2/D3) to your Cogmento account, or use a separate design file that overrides them.
2. Run the FoXYiZ engine from the pilot root with config `y/Cogmento.json`:

   From **Feb_JPACT/Pilot/FoXYiZ** (with fEngine and `x` module available):

   ```bash
   python fEngine.py y/Cogmento.json
   ```

   Or from **Jan2026/Dev/Code-main** with config pointing to this yPAD:

   ```bash
   python fEngine.py path/to/FoXYiZ/y/Cogmento.json
   ```
   (Engine resolves `y/Cogmento/*.csv` relative to the directory containing `fEngine.py`; ensure the FoXYiZ `y` folder is that directory or adjust paths in the config.)

## Plans included

- **PCogmento_OpenBrowser** – open browser, navigate to Cogmento
- **PCogmento_Login_Valid** – valid login, wait for dashboard
- **PCogmento_Login_Invalid** – invalid credentials, verify error
- **PCogmento_Nav_Home / Contacts / Deals / Tasks** – navigation after login
- **PCogmento_Contact_Create** – create one contact (first name, last name, email, save)
- **PCogmento_Logout** – open user menu, logout, verify login page

All locators in `y3Designs.csv` are single **css=** selectors (e.g. `css=input[type='email']`, `css=div#main-nav`). If Cogmento’s DOM differs (e.g. contact form field names), add or edit rows in `y3Designs.csv` and keep using CSS only with no commas in cells.
