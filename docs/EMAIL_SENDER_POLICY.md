# Who our email comes from

**2026-08-14.** A two-phase policy. Phase 1 is in force today and applies to
every new engagement; Phase 2 begins per-client, when MADFAM takes over
managing that client's web presence.

## Phase 1 — MADFAM sends, the platform is credited

Applies from first contact until we manage the client's domain.

```
From:    MADFAM <hola@madfam.io>
Header:  MADFAM
Footer:  © Innovaciones MADFAM S.A.S. de C.V.
         Con tecnología de <platform>   ("Powered by" in en)
```

**Every** message, from **every** platform — Janua, Nauta, Karafiel. The
platform is credited, never branded as the sender.

### Why one sender rather than per-platform

A bespoke client meets several of our platforms over an engagement. A sender
that changes per product teaches them nothing and reads as several vendors.
One consistent sender builds recognition, and recognition is what makes the
*next* email safe to open — which matters most for the first message anyone
receives, a sign-in link.

This is what went wrong before the policy existed: the first message a client
would have received came from `Janua <noreply@janua.dev>` — an unknown brand
on an unrelated domain, asking them to authenticate. Indistinguishable from
phishing, and deleting it is the correct reaction.

### Why not the client's own name on the From line

It was tried and rejected. Sender and destination agreeing sounds right, but
it optimises the wrong thing: the goal in Phase 1 is familiarity with MADFAM,
not the illusion that each product is theirs. Their name belongs on their
workspace, not on our envelope — until Phase 2, when it is genuinely theirs.

### Why not `noreply@<tenant>.madfam.io`

Per-subdomain sending splits reputation across domains that each send a
handful of messages a year, and a domain with no reputation lands in spam. One
verified domain accumulates reputation across every client and every service,
with one SPF/DKIM/DMARC setup instead of N.

**`madfam.io` is Resend-verified** (four months as of 2026-08-14). Verify before
changing a sending domain: sending from an unverified domain is worse than the
wrong brand, because it does not arrive at all.

## Phase 2 — the client's domain, the client's branding

**IN CODE as of 2026-09-06, gated on verification.** Begins per-client when
MADFAM manages that client's web presence (e.g. `creatumundo.mx`).

```
From:    Crea Tu Mundo <hola@creatumundo.mx>
Reply-To: hola@creatumundo.mx
Header:  client logo and palette
Footer:  Con tecnología de MADFAM
```

Owner directive, 2026-09-06: "so far we've been sending the emails from
madfam.io, which should change now that we have @creatumundo.mx accessible via
email. Sender should be hola@creatumundo.mx." `hola@`, matching MADFAM's own
`hola@madfam.io` — a repliable human address, not `noreply@` as this document
originally sketched.

**Precondition, non-negotiable:** the client's domain verified in Resend, which
needs DNS records published — exactly what managing their web presence gives
us. Without it, mail from their domain is not spam-foldered, it is **rejected
by Resend** and never sent at all.

### How the precondition is enforced in code

`RESEND_VERIFIED_DOMAINS` (default `madfam.io`) is the list of domains Resend
has verified. `app/services/email_sender.py::sender_for()` resolves the tenant
from the redirect host (or an explicit `org_id`) and then checks the resolved
address against that list. An address on an unverified domain is **downgraded,
not sent** — and the downgrade is partial:

| `RESEND_VERIFIED_DOMAINS` | A CTM message comes from |
|---|---|
| `madfam.io` | `Crea Tu Mundo <hola@madfam.io>` |
| `madfam.io,creatumundo.mx` | `Crea Tu Mundo <hola@creatumundo.mx>` |

The tenant's **display name** ships immediately; only the **address** waits for
verification. So merging Phase 2 moves no mail, and the production cutover is
one env edit with a one-env-edit rollback — over the same code path that was
already running, which is why the cutover is not also a first execution.

The step-by-step is [`runbooks/resend-domain-onboarding.md`](./runbooks/resend-domain-onboarding.md);
`scripts/resend_domain_onboard.py` creates the domain and prints the exact DNS
records (DKIM `resend._domainkey` TXT, plus `send.` MX + TXT for the SPF return
path) as `enclii providers cloudflare dns-apply` lines.

### The internal door

`POST /api/v1/email/send` accepts `from_email` / `from_name` from other MADFAM
services. These used to be ignored outright. They are now honoured **under the
same gate**: an explicit address is used only when its domain is verified, and
otherwise discarded in favour of the tenant/host rule. A caller's display name
is always honoured — naming yourself is harmless, claiming a domain is not.

## Phase 1, refined — MADFAM sends, the BODY is the tenant's

**2026-08-29.** The sender line above is untouched. What changed is the BODY:
the header wordmark and palette may now read as the client's, with MADFAM
credited underneath. A person signing into their own workspace sees their own
name at the top of the sign-in mail; the envelope is still MADFAM's.

```
From:    MADFAM <hola@madfam.io>            (UNCHANGED — Phase 1)
Header:  the tenant's name and palette      (e.g. "Crea Tu Mundo", indigo)
Footer:  Con tecnología de MADFAM           ("Powered by MADFAM" in en)
```

This is a refinement of Phase 1, not the start of Phase 2. Phase 2 — the
client's DOMAIN on the From line — remains gated on that domain being verified
in Resend, exactly as below. Only the parts of the message that do not affect
deliverability were made per-tenant.

The resolver is `app/services/email_branding.py::resolve_branding()`. It keys on
the magic-link `redirect_url` host (crea-map / kalya → CTM) or an explicit
`org_id`, and returns the header name, header palette, and footer credit;
everything else defaults to the MADFAM frame, so an unknown or absent signal
renders exactly what it rendered before. It is deliberately kept separate from
`resolve_sender`, and nothing it returns is ever used to build the From line.
(Superseded in part by Phase 2 below: the From line DOES now carry the tenant,
but it is resolved by `email_sender.sender_for` from the same host signal —
never from anything `resolve_branding` returns. `test_email_branding.py` still
pins that separation.)

Why keyed on the redirect host rather than `WhiteLabelConfiguration`: the auth
mailer runs in FastAPI BackgroundTasks with no DB session, so the org-branding
table (keyed by `organization_id`) is not reachable at send time. The redirect
host is the tenant signal that IS available — and the one Phase 2 now reads.
When a send path carries a session, `resolve_branding(org_id=…)` is the seam to
hang the DB-backed config on.

## The voice each message speaks in

**2026-09-06.** The From line and the header were already the requester's.
The WORDS were not: every Spanish message addressed its reader as `usted`,
whichever product had asked for it.

Spanish forces a choice English does not — every sentence aimed at the reader
is either `tú` or `usted`, with no neutral second person. The register
machinery has existed in `app/services/email_i18n.py` since the formality work
landed (both copies, both subjects, both templates), but nothing on the live
path ever selected between them: the magic-link router passed `locale` and not
`formality`, so everything resolved through `DEFAULT_FORMALITY` to `usted`.

The result, found live: crea-map's own login page says «Escribe el correo con
el que la dirección te dio de alta — te llega un enlace y con un clic estás
dentro» (`tú`), and the mail janua sent for that page opened «Inicie sesión en
su portal · Use el siguiente botón» (`usted`). Two screens, seen back to back,
addressing the same person two different ways.

### Precedence

Highest first. Each tier is skipped when absent or unsupported, so a bad value
falls through instead of shadowing a good one below it.

| # | Tier | Where it comes from |
|---|------|---------------------|
| 1 | The request | `formality` on `POST /api/v1/auth/magic-link` — `"tu"` or `"usted"` |
| 2 | The reader | `users.spanish_formality`, read by the router while it still holds a session |
| 3 | The product | the redirect host's registered voice — `email_branding.default_formality_for` |
| 4 | The default | `usted` (`email_i18n.DEFAULT_FORMALITY`) |

Tier 3 is the one that fires in practice: `users.spanish_formality` is NULL for
almost every row, because NULL means "has not chosen" rather than "usted". It
is keyed on the SAME redirect host as the branding above, so a message's
header, its voice, and its From line all resolve from one signal:

- CTM products (`crea-map`, `ensayo-map`, `kalya.app`, `*.creatumundo.mx`) → `tú`
- everything else, including the nauta client portal and every unlisted host → `usted`

Tier 2 sitting ABOVE tier 3 is deliberate: a product may state its own voice,
but it must never overwrite someone who has told us how they want to be
addressed.

`formality` is normalized rather than validated: an unsupported value (
`vosotros` included — see `email_i18n` for why that register is not coming)
becomes None and falls to the next tier. A sign-in request must not 422 over a
cosmetic field.

**Consumers:** a product only needs to send `formality` when its voice differs
from its host's registered default. crea-map should send `"tu"` explicitly so
its mail does not depend on a host table entry; nauta needs no change — its
portal hosts already resolve to `usted`, and its request route deliberately
cannot vary its behavior per recipient (that would leak workspace membership).

## The timestamp on every re-sendable subject

**2026-09-06.** Subjects are constant strings, so five requests produce five
messages titled «Su enlace de acceso» — and every mail client threads them
into one conversation. A threaded reader opens the top of the thread, which is
the OLDEST message, lands on an expired link, and has nothing on screen that
distinguishes the live link from the dead ones. Observed on a real inbox as a
single thread labelled «[32] Su enlace de acceso».

Every re-sendable transactional subject now ends with the send moment:

```
Tu enlace de acceso | 2026-09-06 16:23:11
Su enlace de acceso | 2026-09-06 16:23:11
Your sign-in link | 2026-09-06 16:23:11
```

After Anthropic's `Your secure link to Claude.ai is here | 2026-09-06 16:23:11`.
The shape is deliberate: the stamp is LAST so the subject still starts with the
words a reader scans for and a truncating client eats the stamp rather than the
meaning; the date is ISO-ordered and the clock is 24h so it sorts and is
unambiguous between es-MX and en readers; seconds are included because two
links requested in the same minute is exactly the case someone hits when the
first seems not to have arrived.

**The zone is the requester's, and there is no zone suffix.** The stamp is only
useful if the reader can compare it to their own wall clock without arithmetic,
so it is rendered in the product's operating timezone —
`email_branding.timezone_for`, keyed on the same redirect host, defaulting to
`America/Mexico_City` (MADFAM's operating timezone, and the ecosystem rule for
every human-facing time). UTC would read six hours in the future to every
Mexican reader, making the NEWEST link look like it had not arrived yet.

The clock is read per send (`email_i18n.now_for_timezone`), never cached at
import — a module-level "now" would stamp every message in a long-lived worker
with the time that worker booted.

Applies to the three re-sendable messages: **magic link**, **password reset**,
**email verification**. Not to welcome or invitation, which are sent once and
whose subjects already carry a distinguishing organization name.

## The seam that made Phase 2 cheap — now used

`app/services/email_service.py::resolve_sender()` accepted `redirect_url` and
ignored it, with a docstring insisting it was not dead code: "the redirect host
identifies the tenant, so when a client's domain is verified, the switch
happens in one function rather than as another signature change through four
callers."

That is exactly what happened. `resolve_sender` now delegates to
`email_sender.sender_for()`, and no caller signature changed. The prediction is
recorded here because it is the argument for leaving the next such seam alone.

Per-client logo and palette landed earlier, in the Phase-1 refinement above.

## Rules that hold in both phases

- **Never send from an unverified domain.** This is no longer only a habit:
  `RESEND_VERIFIED_DOMAINS` enforces it in code, and adding a domain to that
  list before `scripts/resend_domain_onboard.py` reports `verified` is the one
  way to break it.
- **Credit, do not brand.** Whoever is not the sender goes in "Powered by".
- **es-MX uses "Con tecnología de"**, not "Impulsado por" — the first reads as
  an attribution, the second as marketing.
