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

---

# Quién puede tener remitente de marca

**Sólo los clientes vCTO.** Directiva del propietario, 2026-09-06: «este tipo
de trato debe reservarse exclusivamente para nuestros clientes vCTO, donde
tenemos control operativo completo.»

La razón no es comercial, es operativa. Cuando un correo sale como
`Crea Tu Mundo <hola@creatumundo.mx>`, MADFAM se ha hecho cargo del DNS de ese
dominio, de la rotación de su DKIM, de su reputación de envío y de sus rebotes.
Eso se puede prometer para un cliente retenido cuya infraestructura operamos.
No se puede prometer para un alta self-serve — y prometerlo ahí significa que
el problema de entregabilidad de un desconocido llega como incidente nuestro.

## Dónde vive la verdad

En **janua**, en `product_tiers` de la organización — el mismo almacén de
titularidades que ya alimenta el claim `madfam_entitled_products` del JWT:

```json
{ "vcto": "fractional_cto" }
```

Se otorga y se revoca por el endpoint de admin que ya existe y que ya audita:

```
POST   /api/v1/admin/entitlements/org   {"org_id": "...", "product": "vcto", "tier": "fractional_cto"}
DELETE /api/v1/admin/entitlements/org   {"org_id": "...", "product": "vcto"}
```

**Por qué no se lee de nauta.** Nauta sí tiene el dato (`Workspace.tier =
FRACTIONAL_CTO`), pero (1) no lo expone a ningún llamador de servicio — sus dos
rutas máquina devuelven sólo `{workspaceId, provisioning, locale}` y un
`TimeEntryDraft`; (2) la integración hoy va nauta → janua y nunca al revés,
así que preguntarle obligaría al proveedor de identidad a depender de un
producto aguas abajo en un BackgroundTask, para un enlace de acceso; y (3) el
propio ADR-0001 de nauta declara que «janua es la única autoridad de
titularidades». Preguntarle a nauta invertiría la regla que nauta respeta.

## La compuerta falla cerrada

El mailer corre sin sesión de base de datos, así que la lectura autoritativa no
puede ocurrir en la ruta de envío. La compuerta consulta, en orden: una
decisión explícita del llamador, luego el caché de proceso, y si ninguna
responde **no hay derecho**.

«Falla cerrada» aquí significa que el correo **sí sale**, desde
`hola@madfam.io`, conservando el nombre visible del cliente. Nunca significa
que el enlace de acceso no llegue: un correo que nadie recibe es peor falla que
un correo desde la dirección de la plataforma.

## Matriz de respaldo (fallback)

| vCTO | Dominio verificado en la cuenta que envía | Sale como |
|---|---|---|
| sí | sí | `Crea Tu Mundo <hola@creatumundo.mx>` |
| sí | no | `Crea Tu Mundo <hola@madfam.io>` |
| no | sí | `Crea Tu Mundo <hola@madfam.io>` |
| no | no | `Crea Tu Mundo <hola@madfam.io>` |
| sin señal de inquilino | — | `MADFAM <hola@madfam.io>` |

El degradado siempre es **parcial**: se conserva el nombre, se revierte la
dirección. La marca es cosmética; la dirección es operativa.

---

# Migrar a tu propia cuenta de Resend (u otro proveedor)

Directiva del propietario, 2026-09-06: «debemos permitir mecanismos para que
CTM y cualquier otro cliente vCTO pueda moverse fácilmente a su propia cuenta
de Resend (o su proveedor preferido).»

Un `SenderBinding` (`apps/api/app/services/sender_binding.py`) separa **quién
firma el correo** de **qué cuenta lo envía**. Mudarse de cuenta cambia tres
campos del binding — `account`, `credential_ref`, `verified_domains` — y
**ningún camino de código**. Es reversible en un comando.

> La verificación de dominio en Resend es **por cuenta**. Que
> `creatumundo.mx` esté verificado en la cuenta de MADFAM no dice nada sobre la
> cuenta del cliente. Por eso un binding en cuenta propia lleva su propia lista
> `verified_domains` y deja de consultar `RESEND_VERIFIED_DOMAINS`.

## Orden de operaciones

### 0. La llave, una sola vez, sin eco

El operador pega la API key del cliente una vez y la escribe a Vault. Ni el
script ni el binding ven nunca el valor: el binding guarda una **referencia**.

```bash
read -rs TENANT_RESEND_API_KEY && export TENANT_RESEND_API_KEY
vault kv put secret/janua/senders/ctm resend_api_key="$TENANT_RESEND_API_KEY"
```

### 1. ¿La cuenta del cliente ya tiene el dominio, verificado?

```bash
python3 scripts/sender_binding_switch.py ctm --verify
```

Código de salida `2` = existe pero no verificado. `0` = listo para el paso 3.

### 2. Si no: crearlo ahí e imprimir el DNS que falta

```bash
python3 scripts/sender_binding_switch.py ctm --onboard
```

La clave DKIM es **por cuenta además de por dominio**, así que son registros
**nuevos**, distintos a los que ya están publicados para la cuenta de MADFAM.
El script imprime las líneas `enclii providers cloudflare dns-apply` listas.
Publicarlas por Enclii, esperar propagación, y repetir el paso 1.

### 3. Voltear el binding

```bash
python3 scripts/sender_binding_switch.py ctm --switch \
    --credential-ref 'secret/data/janua/senders/ctm#resend_api_key'
```

Se **rehúsa** a correr si el paso 1 no reporta `verified` (usar `--force` sólo
a sabiendas): voltear antes haría que Resend rechace cada envío del inquilino, y
los enlaces de acceso no llegarían en absoluto.

Edita `sender_binding.py` e imprime el diff. Es un cambio de código a
propósito — el binding es configuración versionada, así que la mudanza se
revisa en un PR y se revierte con `git`. Usar `--dry-run` para verlo sin
escribir.

Antes de desplegar, confirmar que la credencial sí está en Vault (responde
sí/no, nunca imprime el valor):

```bash
python3 scripts/sender_binding_switch.py ctm --check-credential
```

### 4. Reversa

```bash
python3 scripts/sender_binding_switch.py ctm --rollback
```

Vuelve a la cuenta de MADFAM. La línea `From` no cambia; sólo cambia la cuenta
que la transporta. Confirmar que el dominio siga en `RESEND_VERIFIED_DOMAINS`
de la cuenta de MADFAM, o la dirección degradará a `hola@madfam.io`.

## Otro proveedor que no sea Resend

`provider` es un campo del binding (`resend` | `smtp`). El stub `smtp` existe
con la misma interfaz para que «proveedor preferido» sea un cambio de binding y
no de código. **Todavía no tiene transporte detrás**: un binding que declare
`smtp` falla de forma visible en el envío en vez de salir calladamente por
Resend, que sería mentir sobre cómo salió el correo. Implementar el transporte
SMTP es el trabajo pendiente para el primer cliente que lo pida.

## Qué NO hace este procedimiento

- No toca DNS a mano — Enclii-first, por `AGENTS.md`.
- No pone una llave en el repositorio, en un log, ni en un argumento de línea
  de comandos. El binding guarda referencias; Vault guarda valores.
- No cambia la compuerta vCTO. Mudarse de cuenta y tener derecho a remitente de
  marca son decisiones independientes.
