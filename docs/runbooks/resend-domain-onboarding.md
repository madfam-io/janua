# Onboarding a client sending domain in Resend

**Scope:** adding a second sending domain so janua can send transactional mail
*from the client's own address* rather than `hola@madfam.io`. Written for
`creatumundo.mx` (Crea Tu Mundo), which is the first one; the steps generalise.

**Read first:** [`../EMAIL_SENDER_POLICY.md`](../EMAIL_SENDER_POLICY.md). This
runbook executes Phase 2 of that policy. The single precondition the policy
calls non-negotiable is the one this runbook is about: **the domain must be
verified in Resend before janua is told to send from it.**

## The one thing that must not go wrong

Resend does not degrade when you send from a domain it has not verified — it
**rejects the API call**. An unverified sender is not a message in the spam
folder, it is *no message at all*, and the message in question is a sign-in
link. So the code and the cutover are deliberately separated:

| State | `RESEND_VERIFIED_DOMAINS` | A CTM magic link comes from |
|---|---|---|
| Today (code merged, domain not verified) | `madfam.io` | `Crea Tu Mundo <hola@madfam.io>` |
| After verification + manifest edit | `madfam.io,creatumundo.mx` | `Crea Tu Mundo <hola@creatumundo.mx>` |

The display name moves as soon as the code ships; **only the address waits.**
Both states run the same code path, so the cutover is not also a first
execution — `tests/unit/services/test_email_branding.py::
TestSenderUnderTheVerifiedDomainGate::test_ctm_from_is_creatumundo_once_verified`
exercises the post-verification state in CI.

## Precondition: DNS must be ours

`creatumundo.mx` is CTM's domain at Porkbun, and as of 2026-09-06 its
nameservers still point at **Wix**. Records cannot be applied through Enclii
until Switch 1 of the domain plan (nameservers → Cloudflare) is done. Do not
start step 2 before then — the DKIM record simply cannot be published.

## Order of operations

### 1. Create the domain in Resend and read back its DNS

The DKIM public key is generated per-domain, so the records cannot be written
into this runbook ahead of time; they must be read from the API at creation.

```bash
export RESEND_API_KEY=...            # operator env only — never commit, never echo
python3 scripts/resend_domain_onboard.py creatumundo.mx
```

Idempotent: a re-run finds the existing domain instead of creating a duplicate.
It prints the records **and** the matching `enclii providers cloudflare
dns-apply` lines. Exit code `2` means "exists, not verified yet" — expected here.

### 2. Publish the records through Enclii

Enclii-first: do not edit DNS in the Cloudflare dashboard. Copy the generated
lines from step 1 verbatim. Their shape (values are per-domain — use the
script's output, not these):

```bash
enclii providers cloudflare dns-apply resend._domainkey \
  --type TXT --content '<the DKIM value from step 1>' \
  --proxied false --apply \
  --reason 'Resend sending-domain verification for creatumundo.mx'

enclii providers cloudflare dns-apply send \
  --type MX --content '10 feedback-smtp.us-east-1.amazonses.com' \
  --proxied false --apply \
  --reason 'Resend sending-domain verification for creatumundo.mx'

enclii providers cloudflare dns-apply send \
  --type TXT --content 'v=spf1 include:amazonses.com ~all' \
  --proxied false --apply \
  --reason 'Resend sending-domain verification for creatumundo.mx'
```

Three records, in Resend's own vocabulary:

- **DKIM** — `resend._domainkey` TXT, the per-domain public key. This is the one
  that breaks if a character is lost in transcription, which is why step 1
  generates the command rather than asking you to retype it.
- **SPF (return path)** — `send.creatumundo.mx` gets **both** an `MX` and a
  `TXT`. The `send` subdomain is Resend's default custom return path; it is
  what makes SPF align with the envelope sender.
- Note `--proxied false` on every record — these are mail records, and there is
  no TTL flag on `dns-apply`.

**DMARC is optional** for verification and recommended after it: a
`_dmarc.creatumundo.mx` TXT of `v=DMARC1; p=none; rua=mailto:...` starts in
report-only so nothing is rejected while alignment is observed.

### 3. Ask Resend to verify

Propagation is not instant; give the records a few minutes first.

```bash
python3 scripts/resend_domain_onboard.py creatumundo.mx --verify
```

Repeat until it reports `Status : verified` (exit code `0`). `--status` polls
without attempting a re-check. **Do not proceed while this says anything else.**

### 4. Create the `hola@creatumundo.mx` mailbox (Proton)

Resend *sends* as `hola@creatumundo.mx`; nothing *receives* there until the
mailbox exists, and janua sets `Reply-To: hola@creatumundo.mx` on CTM mail. A
family replying to a sign-in mail must land somewhere real.

This is a **manual operator step in the Proton admin console** (stage 4 of the
`creatumundo.mx` domain plan, alongside `admin@creatumundo.mx`) — it is not
automated here and this repo has no Proton credentials. Add `hola@` as an
address/alias on the Proton-hosted domain.

Proton's own MX records are separate from Resend's `send.` return-path MX and
do not conflict — they sit at different names.

### 5. Flip the janua manifest

Only now. In the production janua manifest (the API deployment's env):

```
RESEND_VERIFIED_DOMAINS=madfam.io,creatumundo.mx
```

Keep `madfam.io` in the list — dropping it would downgrade every non-CTM
sender. The value is comma-separated and matched on the **exact** domain, so
`creatumundo.mx` does not authorise `sub.creatumundo.mx`.

This is a plain env change; **no Alembic migration is involved.**

### 6. Smoke: read the actual From header

The API's 200 says nothing about SPF/DKIM alignment or spam placement. Read a
real message.

1. Request a magic link for a CTM user at `https://map.creatumundo.mx` (or
   `crea-map.madfam.io` — both resolve to the CTM tenant).
2. In the received mail, confirm:
   - `From: Crea Tu Mundo <hola@creatumundo.mx>`
   - `Reply-To: hola@creatumundo.mx`
   - `Authentication-Results:` shows `dkim=pass` and `spf=pass`
   - it landed in the **inbox**, not spam
3. Confirm a reply to that address arrives in the Proton mailbox.
4. Confirm a **non-CTM** sign-in (e.g. `janua.dev`) still comes from
   `MADFAM <hola@madfam.io>`.

Step 4 is not optional: the gate is shared, and a mistake in step 5 is most
likely to show up as MADFAM's own mail breaking.

## Rollback

Remove the domain from the verified set and redeploy:

```
RESEND_VERIFIED_DOMAINS=madfam.io
```

CTM mail immediately reverts to `Crea Tu Mundo <hola@madfam.io>` — the display
name is unaffected, only the address falls back, and delivery resumes on a
domain with four-plus months of reputation. No code change, no migration, no
Resend change. The domain can stay registered in Resend while rolled back.

If instead the *default* sender is what broke, the fault is almost certainly a
malformed `RESEND_VERIFIED_DOMAINS` (blank falls back to `madfam.io` by design;
a typo'd value does not). Check the deployed env before touching Resend.

## What this runbook deliberately does not do

- It does not add DNS by hand or via `kubectl` — Enclii-first, per `AGENTS.md`.
- It does not automate Proton. Mailbox creation is an operator action.
- It does not put the API key anywhere but the operator's shell. The script
  reads `RESEND_API_KEY` from env and never prints it or the `Authorization`
  header.
