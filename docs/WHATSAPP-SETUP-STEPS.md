# WhatsApp test-number setup — click by click

Goal: connect Meta's free WhatsApp test number to the platform so you can demo.
~30 min, no cost, no SIM. (Meta's UI moves things around — names may differ slightly.)
IMPORTANT ORDER: set the Render env vars BEFORE configuring the webhook, or Meta's
webhook verification fails.

## STEP 1 — Create the Meta app + add WhatsApp
1. Go to **developers.facebook.com** → log in with your Facebook account → **My Apps** → **Create App**.
2. Use case: choose **Other** → App type: **Business** → name it (e.g. "ReceptionAI") → create.
3. In the app dashboard, find **WhatsApp** → **Set up**. (It may ask to create/select a Meta
   Business Account — create one, any name.)
4. You're now on **WhatsApp → API Setup / Getting Started**. Note these 3 things on that page:
   - **Temporary access token** (a long string) — COPY it. ⚠ Expires in 24h (fine for now; see bottom).
   - **Phone number ID** (a number under "From") — COPY it. (This is NOT the phone number itself.)
   - The **test number** Meta gives you (the "From" number) — this is what you'll message.

## STEP 2 — Get the App Secret
1. Left menu → **App settings → Basic**.
2. Find **App Secret** → click **Show** → COPY it.

## STEP 3 — Set the 3 env vars on Render (DO THIS BEFORE THE WEBHOOK)
1. Go to **dashboard.render.com** → your service (agent-platform) → **Environment**.
2. **Add Environment Variable** three times:
   - `WHATSAPP_ACCESS_TOKEN` = the temporary access token (Step 1)
   - `WHATSAPP_APP_SECRET` = the App Secret (Step 2)
   - `WHATSAPP_VERIFY_TOKEN` = **any string you invent** (e.g. `sky-verify-8842`) — remember it
3. **Save** → Render redeploys (~2–3 min). Wait for it to finish (green "Live").

## STEP 4 — Configure the webhook in Meta
1. Back in Meta → **WhatsApp → Configuration** (or "Webhooks").
2. **Callback URL:** `https://agent-platform-mivq.onrender.com/whatsapp/webhook`
3. **Verify token:** the exact string you set as `WHATSAPP_VERIFY_TOKEN` in Step 3.
4. Click **Verify and Save.** (This works ONLY if Step 3 finished deploying — Meta calls the URL
   and expects your token back.)
5. Under **Webhook fields**, find **messages** → click **Subscribe.**

## STEP 5 — Connect the number to a business
1. Open the platform **dashboard** → sign in → open **Skyline Realty** (or any test business).
2. **Settings** tab → scroll to the **WhatsApp phone_number_id** field.
3. Paste the **Phone number ID** from Step 1 → **Save changes.**

## STEP 6 — Add yourself as a test recipient + test it
1. Meta → **WhatsApp → API Setup** → under "To", **Add recipient** → enter YOUR personal WhatsApp
   number → confirm the code Meta sends you. (Test numbers allow up to 5 recipients.)
2. From your personal WhatsApp, **message the test number** (e.g. "hi, any 2BR in JVC?").
3. The **AI replies** in your WhatsApp chat. 🎉
4. In the platform dashboard → **Conversations** tab → you'll see the thread and can read it.

## If something doesn't work
- **Webhook won't verify:** the Render deploy from Step 3 wasn't finished, or the verify token
  doesn't match exactly. Re-check and retry.
- **No reply from the AI:** confirm you subscribed to the **messages** field (Step 4.5) and pasted
  the **phone_number_id** in Settings (Step 5).
- **"Token expired" after a day:** the temp token lasts 24h. For a lasting setup, create a
  **System User token**: Meta **Business Settings → Users → System Users → Add** → assign the app
  → **Generate token** (select the whatsapp permissions) → put that in `WHATSAPP_ACCESS_TOKEN`.
  It doesn't expire.

## For outbound later (reminders/nurture)
Business-initiated messages outside the 24h window need an approved **utility template**:
Meta **Business Manager → WhatsApp Manager → Message Templates → Create → Utility → submit**
(approved in ~1–2 days). Inbound (Steps above) does NOT need this.
