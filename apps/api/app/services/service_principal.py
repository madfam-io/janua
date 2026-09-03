"""Service principals — the SSOT for "is this identity a person?".

A *service principal*, in janua's sense, is a `User` row that exists so a
system can log in: a development access account, an importer, an integration
principal. It has an email, a magic link and a session, so it is shaped exactly
like a person — and every consuming app therefore renders it as one, in
rosters, in assignee pickers, and in the signature field of documents that are
supposed to name a human being.

Nothing else on the `User` model answers this. `status`, `is_active` and
`is_admin` all describe what a row may DO. `User.is_service_account` is the
first field that describes what it IS.

Not to be confused with
--------------------------
**Machine-to-machine identity**, which has no user row at all: that is an OAuth
`client_credentials` client (`docs/service-tokens.md`, ADR-006), and it is
already solved. A confidential client with a scoped audience is the right shape
for "Zavlo calls Karafiel". This module is for the other half of the problem —
the human-SHAPED logins that are nonetheless not humans, and which no amount of
client-credentials design removes, because a person has to be able to sign in
and look at a screen.

The claim
---------
`is_service_account: true` rides tokens ONLY when the flag is set. It is
absent — not `false` — for everyone else, so the token shape of every person in
the ecosystem is byte-identical to what it was before this existed, and no
consumer's parsing changes because of a claim it has no reason to read.

Consumers read it as a POSITIVE assertion and default to "person" on absence.
That is the safe default here, and deliberately the opposite of the
authorization defaults elsewhere in this file tree: mistaking a service account
for a person shows an operator an extra row in a roster; mistaking a person for
a service account would erase a real colleague from the UI they work in.
"""

from __future__ import annotations

from typing import Any

#: Token claim key. Stamped only when True; see module docstring.
SERVICE_ACCOUNT_CLAIM = "is_service_account"


def is_service_principal(user: Any) -> bool:
    """True when `user` is a technical/service account.

    Tolerant of objects that predate the column (or test doubles that omit it):
    a missing attribute means "person", the same answer every pre-existing row
    gets from the migration's `NOT NULL DEFAULT FALSE`.
    """
    return bool(getattr(user, "is_service_account", False))


def service_principal_claims(user: Any) -> dict[str, Any]:
    """Claims to merge into a token payload for `user`.

    Returns `{"is_service_account": True}` for a service principal and an EMPTY
    dict for a person — so a person's token gains no key at all.
    """
    return {SERVICE_ACCOUNT_CLAIM: True} if is_service_principal(user) else {}


__all__ = [
    "SERVICE_ACCOUNT_CLAIM",
    "is_service_principal",
    "service_principal_claims",
]
