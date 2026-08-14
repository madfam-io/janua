# Who our email comes from

**2026-08-14.** A two-phase policy. Phase 1 is in force today and applies to
every new engagement; Phase 2 begins per-client, when MADFAM takes over
managing that client's web presence.

## Phase 1 — MADFAM sends, the platform is credited

Applies from first contact until we manage the client's domain.

```
From:    MADFAM <noreply@madfam.io>
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

Begins when MADFAM manages the client's web presence (e.g. `creatumundo.mx`).

```
From:    Crea Tu Mundo <noreply@creatumundo.mx>
Header:  client logo and palette
Footer:  Con tecnología de MADFAM
```

**Precondition, non-negotiable:** the client's domain verified in Resend, which
needs DNS records published — exactly what managing their web presence gives
us. Without it, mail from their domain is spam-foldered or rejected.

## The seam that makes Phase 2 cheap

`app/services/email_service.py::resolve_sender()` accepts `redirect_url` and
currently ignores it. **That is not dead code.** The redirect host identifies
the tenant, so when a client's domain is verified, the switch happens in one
function rather than as another signature change through four callers.

The template already takes `platform_name` / `platform_url`, defaulting to
Janua. Per-client logo and palette are the remaining Phase 2 work, and Janua
already models per-org white-label branding to hang them on.

## Rules that hold in both phases

- **Never send from an unverified domain.** Check Resend first, every time.
- **Credit, do not brand.** Whoever is not the sender goes in "Powered by".
- **es-MX uses "Con tecnología de"**, not "Impulsado por" — the first reads as
  an attribution, the second as marketing.
