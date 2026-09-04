# Deploying the dashboard on IIS

This walks through taking the app from "runs on my machine" to "anyone with
the URL can open it" using IIS on your Windows PC. Read the note in
**Step 5** before you decide how far to go — making a home PC reachable from
the whole internet is a real decision, not just a checkbox.

```
Dash app  →  Waitress (WSGI server)  →  IIS (reverse proxy)  →  users
 (app.py)      localhost:8050            port 80 / 443
```

IIS itself doesn't run Python — it sits in front of Waitress (which actually
runs your app) and forwards requests to it. That's what the ARR + URL
Rewrite modules in Step 3 do.

---

## Step 0 — Check what you're starting from

- **Windows edition**: IIS ships with Windows 10/11 Pro/Enterprise and all
  Windows Server editions. (Windows 10/11 Home doesn't include IIS at all —
  if that's you, see the note at the very end.)
- **Python**: 3.10+ installed and on PATH (`python --version` in Command
  Prompt).
- Unzip this project somewhere permanent, e.g. `C:\Apps\rainfall_dashboard`
  — not Desktop or Downloads, since those can get cleaned up.

---

## Step 1 — Get the app running locally first

Open **Command Prompt** or **PowerShell** in the project folder:

```bat
cd C:\Apps\rainfall_dashboard
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python data_prep.py
```

`data_prep.py` only needs to run once (or again later if you refresh the
raw rainfall parquet/shapefile/crop Excel files — see the README).

Now test with the plain dev server:
```bat
python app.py
```
Open `http://127.0.0.1:8050` in a browser. Confirm the Home page, the
Rainfall dashboard, and the Crop Irrigation Calendar all load, then
`Ctrl+C` to stop it. If this doesn't work, nothing past this point will
either — fix it here first.

---

## Step 2 — Run it with Waitress instead

The Flask dev server (`python app.py`) isn't meant for anything but your own
testing. Waitress is a production-grade WSGI server; `server = app.server`
at the top of `app.py` is already set up for it.

```bat
venv\Scripts\activate
waitress-serve --listen=0.0.0.0:8050 app:server
```

Open `http://127.0.0.1:8050` again to confirm it still works — same result,
just a server that can actually handle concurrent users. Leave this running
for now; you'll turn it into a proper background service in Step 5.

---

## Step 3 — Install IIS + the reverse-proxy modules

1. **Turn on IIS** (skip if you already have it):
   *Control Panel → Programs → Turn Windows features on or off* → check
   **Internet Information Services** → OK. Confirm `http://localhost` shows
   the default IIS welcome page.
2. **Install Application Request Routing (ARR)** and **URL Rewrite** — these
   aren't bundled with IIS, they're separate free Microsoft downloads:
   - URL Rewrite: search "IIS URL Rewrite Module download" (Microsoft's own
     download page) → run the installer.
   - ARR: search "IIS Application Request Routing download" → run the
     installer.
   - Restart IIS afterwards (`iisreset` in an admin Command Prompt, or
     restart the machine).
3. **Enable ARR's proxy function** (off by default): open **IIS Manager** →
   click the **server name** (top of the left tree, not a specific site) →
   double-click **Application Request Routing Cache** → in the right-hand
   panel click **Server Proxy Settings** → check **Enable proxy** → Apply.

---

## Step 4 — Point IIS at Waitress

You have two options depending on whether you want the dashboard at the
site root or under a sub-path. **If you're hitting infinite loading or
404/500 errors, it's almost certainly because of a mix-up here** — see the
callout in Option B before you start.

### Option A — dashboard at the root (`http://yourserver/`)
1. In IIS Manager, use **Default Web Site** (or create a new site under
   **Sites → Add Website**, pointing its physical path at any empty folder
   — IIS won't actually serve files from it, it's just a proxy target).
2. Click the site → double-click **URL Rewrite** → **Add Rule(s)** →
   **Reverse Proxy** → enter `localhost:8050` as the server → OK (it'll
   offer to enable proxy again if you missed Step 3.3).

### Option B — dashboard under a sub-path (e.g. `http://yourserver/NKAFC/IMD/RainfallDashboard/`)

> **Do this ONE way, not a mix of the two ways.** A Dash app makes 15-30+
> requests to load one page: the HTML, several JS bundles from
> `/_dash-component-suites/...`, `/_dash-layout`, `/_dash-dependencies`, and
> then a `POST /_dash-update-component` for every chart/table. **All of
> them** need to go through the same rewrite rule. The single most common
> cause of "the page loads but then just spins forever, with some 404s and
> 500s" is that the *first* request (the HTML) got proxied correctly by one
> rule, but the follow-up requests hit a *different* rule (or no rule at
> all) because of exactly this kind of mix-up. So: pick **one** approach
> below and use only that one.

**Recommended: one rule, at Default Web Site level, with the full literal
path.** This is the least ambiguous option and the one this guide assumes
from here on.

1. Don't create `NKAFC`, `IMD`, `RainfallDashboard` as separate
   **Applications** (each with their own Application Pool) — that splits
   the URL space across multiple IIS objects and makes it very easy for the
   rewrite rule to only cover part of it. If you already created them that
   way in IIS Manager, right-click each and **Remove** (this only removes
   the IIS *configuration*, not any files on disk) — you'll recreate the
   URL structure entirely inside a single rewrite rule instead.
2. Select **Default Web Site** in the tree → double-click **URL Rewrite** →
   **Add Rule(s)** → **Blank rule** (not the Reverse Proxy wizard this
   time, so you get full control):
   - **Name**: `RainfallDashboard proxy`
   - **Match URL** → *Requested URL*: `Matches the Pattern`, *Using*:
     `Regular Expressions`, **Pattern**: `^NKAFC/IMD/RainfallDashboard/(.*)`
   - **Conditions**: leave empty (matches all HTTP verbs — GET *and* the
     POST requests Dash's callbacks use).
   - **Action** → *Action type*: `Rewrite`, **Rewrite URL**:
     `http://localhost:8050/{R:1}`
   - Check **Append query string** (on by default — leave it checked;
     Dash's cache-busting `?m=...` on asset URLs needs this).
   - Check **Stop processing of subsequent rules**.
   - OK / Apply.
3. **Also add a redirect for the bare path without the trailing slash** —
   people will type `http://yourserver/NKAFC/IMD/RainfallDashboard`
   (no trailing `/`) and Dash's routing needs that slash. Add a second
   rule, **Add Rule(s) → Blank rule**:
   - **Pattern**: `^NKAFC/IMD/RainfallDashboard$`
   - **Action type**: `Redirect`, **Redirect URL**:
     `/NKAFC/IMD/RainfallDashboard/`, Redirect type `Permanent (301)`.
   - Move this rule **above** the proxy rule from step 2 (select it →
     **Move Rule Up** in the right-hand Actions pane), so the redirect
     happens before the proxy rewrite is considered.
4. The app itself also needs to know this prefix so it builds matching
   asset/API URLs — that's the `DASH_URL_PREFIX` environment variable,
   covered in Step 5. **The site won't work correctly until both this rule
   and that environment variable are set and use the exact same path.**
5. Visit `http://localhost/NKAFC/IMD/RainfallDashboard/` (trailing slash).

Either way, at this point `http://localhost/...` should show the exact same
dashboard as `http://localhost:8050` did — IIS is now just relaying traffic
to Waitress.

---

## Step 4.5 — Diagnose before moving on (do this if you're seeing 404/500/infinite loading)

Don't go to Step 5 until this step is clean — troubleshooting gets much
harder once IIS, the Windows Firewall, and your router are all in the mix.

**The single most useful tool here is your browser's Network tab.** Open the
dashboard, press **F12**, click the **Network** tab, tick **Preserve log**,
then reload the page. Let it spin for a few seconds, then look at the list:

1. **Find the requests shown in red / with a 404 or 500 status.** Click one
   → the **Headers** tab shows the exact URL it requested. This tells you
   precisely what's broken — you don't have to guess:
   - If the failing URLs are missing the `NKAFC/IMD/RainfallDashboard`
     prefix (e.g. it requested `/assets/style.css` instead of
     `/NKAFC/IMD/RainfallDashboard/assets/style.css`) → `DASH_URL_PREFIX`
     isn't set on the Waitress service, or doesn't match the rewrite rule.
     Fix in Step 5.
   - If the failing URLs **do** have the correct prefix but still 404 →
     the rewrite rule itself isn't catching them (see the "one rule, one
     way" callout above — you likely have a second, conflicting
     Application/rule only covering part of the path).
   - **500 errors on `_dash-update-component` (POST requests) specifically**
     → almost always means the rewrite rule's **Conditions** section
     accidentally restricts it to GET only, or a `web.config` inherited
     from a parent folder is blocking POST. Re-check the rule has no verb
     condition (Step 4.2 above), and see the `web.config` note below.
2. **Isolate which layer is broken** by testing each one directly, in
   order — stop at the first one that fails, that's where the problem is:
   - **Waitress directly, bypassing IIS entirely**: if `DASH_URL_PREFIX` is
     already set on the service, test
     `http://127.0.0.1:8050/NKAFC/IMD/RainfallDashboard/`; if you haven't
     set it yet, test plain `http://127.0.0.1:8050/`. If this fails, the
     problem is in the app/Waitress, not IIS at all — go back to Step 1-2.
   - **Through IIS, same machine**:
     `http://localhost/NKAFC/IMD/RainfallDashboard/`. If the previous test
     passed but this one fails, the problem is the IIS rewrite rule.
   - **Through IIS, from another device on your network**:
     `http://<LAN-IP>/NKAFC/IMD/RainfallDashboard/` (find the LAN IP with
     `ipconfig`). If the previous test passed but this fails, it's the
     Windows Firewall (Step 6), not IIS.
3. **Check the IIS logs** for the exact sub-status code (more specific than
   what the browser shows): `C:\inetpub\logs\LogFiles\W3SVC1\` (folder
   number may differ — check **Sites → Default Web Site → Logging** in IIS
   Manager for the exact path). A `404.11` specifically means "double
   escaping" was blocked — fix with the `web.config` addition below. A
   `500.19` means a `web.config` itself is malformed or a setting is locked
   at the server level.
4. **A `web.config` safety net.** If you're still seeing scattered 404s for
   `_dash-component-suites` paths after the above, add this
   `web.config` in the same folder as the URL Rewrite rule (Default Web
   Site's physical root) to stop IIS's request filtering from interfering —
   IIS Manager normally maintains this file for you when you add rules
   through the UI, but it's worth confirming these two settings are present
   inside the existing `<system.webServer>` section:
   ```xml
   <security>
     <requestFiltering allowDoubleEscaping="true" />
   </security>
   ```
5. **Confirm Anonymous Authentication is enabled.** Select **Default Web
   Site** → **Authentication** → **Anonymous Authentication** should be
   **Enabled**; if **Windows Authentication** is enabled instead (or
   *also*), external users will get 401s that can look like generic
   failures. For a public dashboard, Anonymous should be the only one
   enabled.

Once the Network tab shows every request succeeding (status 200/304) and
the dashboard actually renders at `http://localhost/NKAFC/IMD/RainfallDashboard/`,
move on to Step 5.

---

## Step 5 — Make it permanent: Waitress as a Windows Service

Right now Waitress only runs while your Command Prompt window is open, and
stops if you log out or reboot. **NSSM** (Non-Sucking Service Manager, a
free tool) turns it into a proper background service.

1. Download NSSM (search "nssm.cc download"), extract `nssm.exe` somewhere
   like `C:\Apps\nssm\nssm.exe`.
2. Open an **admin** Command Prompt:
   ```bat
   C:\Apps\nssm\nssm.exe install RainfallDashboard
   ```
3. In the dialog that opens:
   - **Path**: `C:\Apps\rainfall_dashboard\venv\Scripts\waitress-serve.exe`
   - **Startup directory**: `C:\Apps\rainfall_dashboard`
   - **Arguments**: `--listen=0.0.0.0:8050 app:server`
   - **If you're using Option B** (a sub-path like
     `/NKAFC/IMD/RainfallDashboard/`), go to the **Environment** tab and add:
     ```
     DASH_URL_PREFIX=/NKAFC/IMD/RainfallDashboard/
     ```
     (leading *and* trailing slash, matching the URL Rewrite pattern from
     Step 4 exactly). Skip this for Option A (root deployment).
   - On the **Details** tab, give it a display name so it's identifiable in
     Services.
   - Click **Install service**.
4. Start it: `net start RainfallDashboard` (or find "RainfallDashboard" in
   **Services** (`services.msc`) and start it there — set **Startup type**
   to **Automatic** so it survives reboots).

If you already installed the service before setting the environment
variable, update it without reinstalling:
```bat
C:\Apps\nssm\nssm.exe set RainfallDashboard AppEnvironmentExtra DASH_URL_PREFIX=/NKAFC/IMD/RainfallDashboard/
net stop RainfallDashboard
net start RainfallDashboard
```

From now on, Waitress runs whether or not you're logged in, and restarts
automatically if the machine reboots. Re-check `http://localhost` to
confirm IIS + the service together still serve the dashboard.

---

## Step 6 — Open it up

### Same network only (office/home Wi-Fi)
- Windows Firewall: **Control Panel → Windows Defender Firewall → Advanced
  Settings → Inbound Rules → New Rule** → Port → TCP 80 (and 443 if you set
  up HTTPS) → Allow.
- Anyone on the same network can now reach it at `http://<your-PC's-LAN-IP>`
  (find that IP with `ipconfig`). This is often good enough for a
  university department or office setting.

### Anywhere on the internet
This needs two more things a LAN doesn't:
1. **Port forwarding on your router**: forward external port 80 (and 443)
   to your PC's LAN IP, port 80/443. Steps vary by router brand — search
   "[your router model] port forwarding".
2. **A stable address to give people**: most home/office internet
   connections get a public IP that changes periodically, so `http://<ip>`
   will stop working after a while. Use a **Dynamic DNS** service (e.g. No-IP,
   DuckDNS — both have free tiers) to get a fixed hostname like
   `nkafc-rainfall.duckdns.org` that keeps pointing at your current IP.
3. **Verify the port forward actually works from outside** before telling
   anyone the URL: use a site like `canyouseeme.org`, enter port `80`, and
   check it. If it fails here, don't go looking for problems in IIS — it's
   the router config or your ISP blocking the port (common on residential
   and mobile broadband plans; worth a quick call to them if the router
   config looks correct but this still fails).

> **Before you do this**: exposing a personal Windows PC to the open
> internet is a genuinely different risk profile than a LAN-only deployment
> — it's now a target for internet-wide scanning and attack attempts, not
> just your own network. At minimum: keep Windows fully patched, don't
> forward any other ports, and consider adding HTTPS (below) since plain
> HTTP sends everything, including anything typed into forms, in the clear.
> If this dashboard is meant to be permanently public, a small cloud VM
> (DigitalOcean, Azure, AWS — a few dollars/month) is a more robust and
> isolated place for it than a personal machine, and sidesteps the dynamic
> IP / home-router-reliability issues entirely. I'm glad to write that
> deployment path too if you'd rather go that way.

---

## Step 7 (recommended if going public) — HTTPS

Once you have a DNS hostname pointing at your PC (Dynamic DNS or otherwise),
**win-acme** gets you a free Let's Encrypt certificate and wires it into IIS
automatically:
1. Download win-acme (search "win-acme download").
2. Run `wacs.exe` as admin, follow the prompts (it detects your IIS site
   and binding automatically).
3. It also sets up auto-renewal, so you don't have to repeat this every 90
   days.

---

## Memory footprint & how many concurrent users this can handle

If you're hosting this anywhere with a RAM limit (Render's free tier is
512MB, for example), these are real measured numbers, not estimates -- run
`python -c "import app"` and watch `/proc/<pid>/status`'s `VmRSS` yourself
if you want to reproduce them.

**Idle footprint (just imported, before serving any request): ~263MB.**
This used to be ~395MB; three fixes brought it down:
1. `daily.parquet` (1.2M rows) was storing taluk/district names as full
   repeated strings. `data_prep.py` now writes it (and the other processed
   tables) with compact dtypes -- categorical text, float32 rainfall, small
   integer types -- cutting that file's memory cost by roughly half. If you
   regenerate the processed data from a different source, re-run
   `python data_prep.py` to get the compact version.
2. `exports.py` was independently re-parsing the same taluk boundary file
   that's already loaded elsewhere in the app (~36MB wasted). Fixed to
   reuse the already-loaded copy.
3. `matplotlib` (~25MB) used to load at server startup even though it's
   only needed for PDF/PNG/graph-image downloads. It's now lazy-loaded on
   first actual use, so a process that's only ever served map/chart views
   never pays that cost at all.

**Per-request cost, measured:**
| Request | Time | Memory added |
|---|---|---|
| Normal page interaction (charts, KPIs, map) | ~13ms | ~2-3MB |
| Excel workbook | ~500ms | ~15-20MB |
| PDF report, first one any worker generates | ~1.1s | ~50MB (includes matplotlib's one-time load) |
| PDF report, subsequent ones | ~750ms | ~10MB each |

So after a process has handled its first PDF/PNG/ZIP request, its baseline
effectively rises to ~310-320MB and stays there. On a 512MB host that
leaves roughly 190-200MB of headroom for everything else happening at
once -- which is comfortable for normal browsing by many simultaneous
users (that costs almost nothing per request), but gets genuinely tight if
several people request PDF/Excel/ZIP downloads at the same moment, since
each one transiently costs 10-50MB. Waitress's default thread pool (4
threads) naturally caps how many requests run at once in a single process,
which helps, but doesn't eliminate the risk on the smallest tiers.

One more thing worth knowing: Python/glibc don't always return freed memory
to the OS promptly (a well-known allocator behaviour, not a bug in this
app), so RSS can creep upward gradually over a long-running process's
lifetime under sustained heavy use. This isn't a leak -- restarting the
process (or a host that periodically recycles workers) resets it -- but on
a 512MB box it's one more reason not to run right at the edge for weeks at
a time unmonitored.

**If deploying with gunicorn (Render, most Linux PaaS hosts) rather than
Waitress**: every number above is *per worker process* -- gunicorn can run
multiple worker processes, each with its own full copy of this app in
memory, and `--workers N` (or Render's `WEB_CONCURRENCY` env var, if your
start command references it) multiplies the footprint by N. On a 512MB
instance, stick to a single worker (`gunicorn app:server` with no
`--workers` flag defaults to 1) -- concurrency within that one process is
still handled fine by gunicorn's own request threading, you just don't want
N independent ~263MB copies competing for 512MB total.

**Recommendation for "anyone in India can access this":**
- **Render's free tier specifically** has two separate problems, not just
  RAM: it also spins the whole service down after ~15 minutes of no
  traffic, so the first visitor after any quiet period waits 30-60+ seconds
  for a cold start. That's very likely a big part of the "very lag" you
  saw, independent of the memory fixes above. Render's cheapest **paid**
  tier removes the cold-start spin-down and gives more RAM headroom, so if
  you stay on Render, that's the one upgrade that matters most.
- **Your own IIS setup (Steps 0-7 above)**, if you have access to
  reasonably specced institutional hardware, sidesteps this whole question
  -- a normal PC or server has multiple GB of RAM, comfortably clearing
  every number above with no ongoing hosting cost. This is the path I'd
  actually recommend for a public agromet service, if the hardware access
  is there.
- If neither of those fits, a small VPS (DigitalOcean/Linode/AWS
  Lightsail, ~$5-6/month for 1GB RAM) gives roughly double this app's idle
  footprint in headroom, no cold starts, and full control -- a reasonable
  middle ground between Render's free tier and running your own server.

---

## Troubleshooting

- **Page spins/loads forever, with some 404s and/or 500s showing up**: this
  is covered in detail in **Step 4.5** above — open the browser's Network
  tab (F12), find the failing requests, and follow the diagnosis there. In
  short, it's almost always either (a) the URL Rewrite rule not covering
  every request Dash makes, or (b) `DASH_URL_PREFIX` not matching that rule
  exactly.
- **Page loads under the sub-path but looks unstyled/broken, or the map and
  charts never appear**: `DASH_URL_PREFIX` isn't set (or doesn't exactly
  match the URL Rewrite pattern) on the Waitress service. Check your
  browser's dev tools (F12) → Network tab for `/assets/...` requests coming
  back 404 — that confirms it. Fix with the `nssm set` command in Step 5.
- **IIS shows a 502/504 error**: Waitress isn't running, or ARR proxy isn't
  enabled (Step 3.3). Check `services.msc` for the `RainfallDashboard`
  service status, and confirm `http://localhost:8050` still works directly.
- **Works on `localhost` but not from another device**: almost always the
  Windows Firewall rule (Step 6) — port 80 isn't actually open yet.
- **Works on LAN but not from outside**: router port forwarding isn't
  configured, or your ISP blocks inbound port 80 (some do, especially on
  residential/mobile plans — worth checking with them if forwarding looks
  correct but nothing gets through).
- **Maps or charts look broken only in production, not locally**: usually a
  missing package — re-run `pip install -r requirements.txt` inside the
  venv the service actually uses.

---

## If you're on Windows 10/11 **Home** (no IIS available)

Home editions don't include IIS at all. The simplest alternative that keeps
the same overall shape (Waitress serving the app, something else fronting
it) is swapping IIS for **Caddy** or **nginx** as the reverse proxy — both
run as a single executable with a short config file, no Windows feature
install required. Happy to write that version of this guide instead if
that's your situation.
