#!/usr/bin/env bash
# Prove hola@madfam.io can SEND and RECEIVE, using the real client email.
#
# WHY NOT A "hello world" TEST. A plain test message proves the mailbox exists
# and nothing else. This renders the ACTUAL es-MX magic-link template — the
# exact bytes Alejandra receives — and sends it hola@ -> hola@, so one message
# settles four things at once:
#
#   1. Resend accepts hola@madfam.io as a sender (domain verified).
#   2. The ProtonMail alias RECEIVES at hola@madfam.io.
#   3. The frame renders MADFAM, not Janua — header, footer, "Con tecnología de".
#   4. It lands in the inbox rather than spam, which is the thing that actually
#      decides whether a client ever sees a sign-in link.
#
# Read the RECEIVED message, not just the 200: SPF/DKIM alignment and spam
# placement are invisible from the API response.
#
# USAGE
#   RESEND_API_KEY=re_xxx bash scripts/send-sender-identity-test.sh
#   RESEND_API_KEY=re_xxx TO=someone@else bash scripts/send-sender-identity-test.sh
set -euo pipefail

: "${RESEND_API_KEY:?Set RESEND_API_KEY (Resend dashboard -> API keys)}"
FROM_ADDR="${FROM_ADDR:-hola@madfam.io}"
TO="${TO:-hola@madfam.io}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

HTML=$(python3 - "$ROOT" <<'PY'
import sys
from jinja2 import Environment, FileSystemLoader
root = sys.argv[1]
env = Environment(loader=FileSystemLoader(f"{root}/apps/api/app/templates/email"))
tr = {
    "tagline": "Tecnología, diseñada para tu operación",
    "rights": "Todos los derechos reservados.",
    "powered_by": "Con tecnología de",
    "privacy": "Aviso de privacidad",
    "terms": "Términos del servicio",
    "support": "Soporte",
    "why_received": "Recibió este correo electrónico porque tiene una cuenta con MADFAM.",
    "location": "Innovaciones MADFAM S.A.S. de C.V. • Cuernavaca, Morelos, México",
}
html = env.get_template("es/magic_link.html").render(
    t=lambda k: tr.get(k, k), lang=lambda: "es-MX", current_year=2026,
    subject="Inicia sesión en Crea Tu Mundo", user_name="Aldo",
    magic_link="https://crea.madfam.io/portal/verify?token=PRUEBA-NO-FUNCIONAL",
    expires_in_minutes=15,
)
# Fail loudly rather than send a wrong-looking test: a green send of a
# Janua-branded email would be worse than no test at all.
assert ">MADFAM<" in html, "header is not MADFAM"
assert "Con tecnología de" in html, "powered-by missing"
assert "Cuernavaca" in html, "footer address not corrected"
assert "cuenta en Janua" not in html, "Janua account line still present"
print(html)
PY
)

printf 'Rendered %s bytes. Sending %s -> %s …\n' "${#HTML}" "$FROM_ADDR" "$TO" >&2

# NOT piped and NOT chained: the exit status must be this call's own.
RESPONSE=$(curl -sS -w '\n%{http_code}' -X POST https://api.resend.com/emails \
  -H "Authorization: Bearer ${RESEND_API_KEY}" \
  -H "Content-Type: application/json" \
  --data @<(python3 -c '
import json,os,sys
print(json.dumps({
  "from": f"MADFAM <{os.environ[\"FROM_ADDR\"]}>",
  "to": [os.environ["TO"]],
  "subject": "[PRUEBA] Inicia sesión en Crea Tu Mundo",
  "html": sys.stdin.read(),
}))' <<< "$HTML"))

CODE=$(printf '%s' "$RESPONSE" | tail -n1)
BODY=$(printf '%s' "$RESPONSE" | sed '$d')

if [ "$CODE" != "200" ]; then
  echo "FAILED: Resend answered HTTP ${CODE}" >&2
  echo "$BODY" >&2
  echo >&2
  echo "422 with 'domain is not verified' means madfam.io lost verification." >&2
  echo "403 usually means the API key lacks send permission." >&2
  exit 1
fi

echo "Resend accepted it: $BODY"
cat >&2 <<'NOTE'

SENT — but a 200 only means Resend TOOK it. Now check the inbox, because the
things that actually matter are invisible from here:

  [ ] It arrived at hola@madfam.io at all (the Proton alias exists and routes).
  [ ] It is in the INBOX, not spam.
  [ ] The From reads  MADFAM <hola@madfam.io>  — not Janua, not noreply.
  [ ] The header says MADFAM and the footer says "Con tecnología de Janua".
  [ ] Replying to it lands somewhere a human reads.

That last one is the whole reason we moved off noreply@. Test it: hit reply.
NOTE
