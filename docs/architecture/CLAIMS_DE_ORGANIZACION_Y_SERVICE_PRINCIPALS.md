# Claims de organización y service principals

> Contrato de claims para las apps del ecosistema. Última revisión: 2026-09-02.

Dos cambios que van juntos y **no deben separarse**:

1. Los tokens de sesión (enlace mágico, contraseña, MFA, passkey) ahora sellan
   `org_id` — igual que los de OIDC.
2. Los roles de organización viajan bajo una clave **con espacio de nombres**,
   `madfam_org_roles`, nunca bajo `roles` a secas.

El punto 2 es lo que evita que el punto 1 sea una fuga. Está explicado abajo.

---

## 1. El problema que resuelve

`symbiosis-hcm` exige `org_id` en el token y responde **403** sin él
(`apps/api/core/permissions.py`). janua sí sellaba `org_id`… pero **solo en el
camino OIDC**. El camino de enlace mágico —`AuthService.create_session`— no lo
sellaba nunca, porque el resolvedor de claims vivía dentro del router de OIDC y
era estructuralmente inalcanzable desde el servicio de sesiones.

Consecuencia concreta: el equipo de CTM entra al MAP clínico por enlace mágico.
Al pulsar «Mi espacio (RH)» llegaban a una app que **carga y los rechaza**.
Peor que un 404, porque parece un problema suyo.

## 2. La trampa que había armada

`HR_ROLES` de symbiosis-hcm contenía la cadena literal `"admin"`. Los `roles`
que janua sella por OIDC son roles de **membresía de organización**
(`owner`/`admin`/`member`): permisos sobre la **cuenta** —invitar a alguien,
rotar un secreto, pagar la factura—, no sobre nómina.

Lo único que separaba a un `admin` de organización de la nómina, los salarios,
el SDI y los expedientes laborales del tenant era que su token **no traía
`org_id`** y la verificación de tenant lo rechazaba primero.

**Sellar `org_id` sin arreglar el espacio de nombres de los roles convierte un
403 honesto en una fuga de nómina**, en silencio, para todo `admin` de toda
organización. Por eso los dos cambios van juntos, y por eso hay pruebas que
fallan si alguien «simplifica» el namespace de vuelta.

## 3. Forma de los claims

Resueltos por `app/services/org_claims_service.py`, la **única** fuente. El
router de OIDC lo importa; no hay una segunda copia (dos copias de un
resolvedor de autorización derivan, y una copia derivada falla o cerrada —
alguien deja de trabajar— o abierta — alguien gana un tenant).

| Claim | Tipo | Cuándo se emite | Significado |
|---|---|---|---|
| `orgs` | lista de `{id, slug, role}` | con ≥1 membresía **activa** | todas las membresías activas |
| `org_id` | string (UUID) | solo si **no hay ambigüedad** | el tenant primario |
| `tenant_id` | string (UUID) | igual que `org_id` | alias de `org_id` |
| `org_slug` | string | igual que `org_id` | slug del tenant primario |
| `madfam_org_roles` | lista de strings | igual que `org_id` | rol de organización **en esa org** |
| `roles` | lista de strings | **solo** con concesiones vivas | roles de **aplicación** (`hcm:hr`), ver §5 |
| `is_service_account` | `true` | **solo** si la identidad es técnica | ver §6 |

**«Sin ambigüedad»** significa: exactamente una membresía activa, o
`user.tenant_id` nombra una de ellas. Con varias organizaciones y sin ancla, se
emite `orgs` **y nada más** — ningún consumidor debe adivinar un tenant.
Adivinar el tenant primario de un usuario multi-org es exactamente cómo el
operador de un tenant termina leyendo la nómina de otro.

Ejemplo (token de sesión de un integrante de CTM):

```jsonc
{
  "sub": "…", "tid": "…", "type": "access", "email": "…",
  "madfam_entitled_products": ["crea-map:pro", "kalya:team"],
  "orgs": [{ "id": "<uuid>", "slug": "crea", "role": "member" }],
  "org_id": "<uuid>",
  "tenant_id": "<uuid>",
  "org_slug": "crea",
  "madfam_org_roles": ["member"]
}
```

### Invariantes

- **Aditivo.** Un usuario sin membresía activa recibe un token con la forma
  exacta de antes: ninguna de estas claves aparece.
- **`roles` no cambia.** El camino OIDC sigue emitiéndolo igual para los
  clientes que ya lo leen. Los tokens de **sesión** no lo emiten: estrenan el
  claim con namespace, sin heredar la ambigüedad.
- **Fail-closed.** Si la resolución falla, no se emite ningún claim de
  organización. Los servicios con alcance de org rechazan; nunca mal-asignan.
- **Nunca bloquea el login.** Un fallo del resolvedor degrada a «sin claims»,
  no a un 500.
- **No se puede suplantar.** `additional_claims` se mezcla **antes** que las
  claves reservadas (`sub`/`tid`/`jti`/`type`/`exp`/`iss`/`aud`), así que un
  dict hostil o con bug no puede reescribir la identidad del token.
- **La revocación llega al refresh.** El resolvedor filtra
  `status == "active"`, y `refresh_tokens` vuelve a resolver: una membresía
  revocada deja de alimentar el claim en la siguiente rotación.

### Para quien consume

`madfam_org_roles` describe autoridad sobre la **cuenta de janua** y no debe
autorizar nada dentro de un producto. Los roles de **aplicación** —los que sí
autorizan dentro de un producto— viajan bajo `roles` y se conceden
explícitamente por organización: ver §5. La regla que no cambia es que el
**vocabulario** de roles lo sigue definiendo el servidor de recursos
(`symbiosis-hcm/apps/api/core/roles.py`); janua sólo registra **a quién** se le
concedió **qué**, por quién y cuándo.

---

## 4. Service principals

`User` distinguía `status`, `is_active`, `is_admin` y `tenant_id`. Ninguno
responde la pregunta que una app consumidora realmente hace: **¿esta fila es
una persona?**

Todo tenant multi-app acaba con logins técnicos —un acceso de desarrollo, un
importador, un principal de integración—, y sin esta marca aparecen en cada
roster, cada selector de asignación y cada campo de firma de documento como si
fueran colegas.

`User.is_service_account` (migración `015_user_is_service_acct`) es el primer
campo del modelo que describe **qué es** la fila, no qué puede hacer.

### No confundir con tokens de servicio

| | Service **token** | Service **principal** |
|---|---|---|
| Qué es | cliente OAuth `client_credentials` | fila `User` marcada |
| Tiene fila de usuario | no | sí |
| Para qué | Zavlo llama a Karafiel | una persona-máquina inicia sesión y ve una pantalla |
| Documentación | `docs/service-tokens.md`, ADR-006 | este documento |

Son problemas distintos. Los tokens de servicio ya estaban resueltos; esto es
la otra mitad, la de los logins **con forma humana** que aun así no son humanos.

### Superficies

- **Claim** `is_service_account: true` — en tokens de sesión y de OIDC. Se sella
  **solo** cuando es verdadero: el token de una persona no gana ninguna clave y
  su forma es idéntica a la de antes.
- **`GET /api/v1/users/me`, `/users/{id}`, `/users/`** — campo
  `is_service_account`.
- **`GET /api/v1/organizations/{id}/members`** — campo `is_service_account`,
  resuelto desde la identidad (no desde la fila de membresía: ser cuenta de
  servicio es un hecho de la **identidad**, verdadero en todas sus orgs, y una
  org no puede discrepar de otra al respecto). Se calcula **después** de la
  caché de Redis del servicio, para que una caché vieja nunca afirme que un
  login técnico es una persona.
- **`POST /api/v1/internal/users/provision`** — acepta `is_service_account`
  (por defecto `false`) y lo devuelve; acepta `org_role` (por defecto `member`)
  y devuelve el rol de la membresía activa resultante en `org_role`.

### La regla del provisioning

`provision` **honra la bandera solo al crear**. Una fila existente se devuelve
intacta —igual que ya pasaba con el nombre—: cambiar una identidad viva entre
«persona» y «servicio» tiene consecuencias visibles en rosters y en firmas de
documentos, y no debe ocurrir como efecto secundario del reintento de una app
de roster. La respuesta echa el valor **almacenado**, para que quien llame
detecte el caso sin una segunda lectura.

### La membresía es la excepción a esa regla

Escribir `tenant_id` en la fila del `User` **no otorga acceso**. El resolutor de
claims cuenta únicamente membresías con `status == "active"`, así que una
identidad con `tenant_id` y **sin** `OrganizationMember` recibe un token **sin
`org_id`** — y HCM la rechaza con 403. Por eso `provision` crea (o reconcilia)
la membresía activa en **la misma transacción** que el usuario, y lo hace en
**ambas** ramas, la de creación y la de «ya existía»: reconciliarla en la rama
de 200 es lo que **repara a quienes se provisionaron antes de este cambio**, que
de otro modo quedarían fuera de «Mi espacio (RH)» para siempre.

- **`org_role`** (opcional, por defecto `member`) elige el rol de la membresía.
  Está acotado a `admin` · `member` · `viewer`: el valor viaja al claim
  `madfam_org_roles`, y una cadena libre dejaría que una app de roster acuñe una
  autorización arbitraria. **`owner` no se ofrece**: la propiedad de una
  organización es una decisión de operador, no algo que conceda un «Alta de
  integrante».
- **No degrada un rol existente.** Si ya hay membresía activa se devuelve tal
  cual: un ascenso hecho por un operador sobrevive al reintento del roster,
  igual que sobrevive el nombre.
- **Re-alta.** Una membresía `removed`/`inactive` se **revive** (no se duplica),
  porque el reintento del roster es precisamente la re-alta.
- La respuesta trae **`org_role`** (o `null` si no hay membresía), para que la
  app de roster verifique que la persona llevará `org_id` sin decodificar un
  token.

### Cómo leerlo (para consumidores)

Trátalo como una **afirmación positiva**: ausente ⇒ persona. Es la dirección
segura, y es deliberadamente la contraria a los defaults de autorización de
este repo: confundir una cuenta de servicio con una persona muestra una fila de
más en un roster; confundir una persona con una cuenta de servicio **borraría a
un colega** de la interfaz donde trabaja.

La bandera **no autoriza ni desautoriza nada**. Es un hecho de presentación. Si
llegara a conceder o quitar acceso, un operador tendría dos palancas donde cree
tener una.

---

## 5. Roles de aplicación (`hcm:hr` y compañía)

### El hueco que quedaba

Poner espacio de nombres a `madfam_org_roles` (§2) era lo correcto y **dejó la
otra mitad sin construir**. symbiosis-hcm autoriza con roles de **aplicación**
que lee del claim `roles` —`hcm:hr`, `hcm:admin`, `employee`
(`apps/api/core/permissions.py`)— y **janua no emitía ni una sola cadena
`hcm:*`**. Es decir: la Dirección de CTM podía tener una membresía válida,
recibir un token con `org_id` correcto (§4 y janua#591)… y aun así ser rechazada
en todas las funciones de RH. La membresía respondía *cuál inquilino*; nada
respondía *cuál autoridad dentro del producto*.

### La forma

Una concesión = una fila en `organization_member_app_roles` (migración `016`),
colgada de la **membresía**, no del usuario:

| Columna | Para qué |
|---|---|
| `organization_member_id` | la membresía que la porta (FK, `ON DELETE CASCADE`) |
| `app` · `role` | **opacos** para janua: `hcm` · `hr` |
| `granted_by` · `granted_at` | quién la concedió y cuándo |
| `revoked_at` · `revoked_by` | quién la retiró y cuándo |

El resolutor las convierte en `"<app>:<role>"` y las sella bajo `roles`.

**Por qué una tabla y no un JSONB en la membresía.** Esto concede autoridad
sobre **nómina y expedientes laborales**, así que los dos datos que un auditor
pide —quién la dio y cuándo se quitó— tienen que sobrevivir a la concesión. Una
lista JSONB guarda sólo el estado actual: revocar es una reescritura en sitio
que **borra la evidencia** de que la concesión existió. Las filas se retiran con
`revoked_at`, nunca se borran, igual que `capability_links` (§ADR-004) y por la
misma razón por la que `internal_users` no tiene endpoint de purga.

**Por qué cuelga de la membresía y no del usuario.** Una concesión no significa
nada fuera de la membresía que la porta: si alguien sale de la organización, su
autoridad de RH se va con el inquilino en vez de quedar como fila huérfana que
un futuro re-alta reanimaría en silencio. Además hace que la fuga entre
organizaciones sea **estructuralmente difícil de escribir**: el resolutor parte
de UNA fila de membresía y no puede alcanzar las concesiones de otra org.

### Las tres reglas de alcance

- **Sólo la org primaria resuelta aporta.** Sin `org_id` inequívoco no hay
  `roles` tampoco: elegir una de varias membresías entregaría la autoridad de RH
  de un inquilino a una sesión que la persona abrió para otro.
- **Nada es implícito.** No hay derivación desde `member.role`, ni conjunto por
  defecto, ni tabla que convierta un `admin` de organización en `hcm:admin`.
  Cualquiera de esas reconstruiría **por la puerta de atrás** el puente
  rol-de-cuenta → nómina que el espacio de nombres existe para impedir. Una
  cuenta de servicio se trata igual que una persona: lo que se le concedió
  explícitamente, y nada más.
- **La revocación llega al refresh.** El resolutor filtra `revoked_at IS NULL` y
  todos los caminos de emisión re-resuelven.

### La trampa del `roles` heredado

El camino OIDC **ya emitía** su propio `roles` (roles de organización, para
clientes que lo leen desde hace años, y que contiene la cadena `"admin"`). En
ese handler `**org_claims` se expande **después** de `"roles": entitlements[...]`,
así que una clave `roles` saliendo del resolutor **habría pisado el claim
heredado** por puro orden de diccionario. Por eso el resolutor devuelve la clave
privada `_app_roles` y `merge_app_roles_into_claims` la integra una sola vez
para ambos caminos:

- **Tokens de sesión**: sólo roles de aplicación. Siguen sin llevar ningún rol de
  organización bajo `roles` — lo que aterriza ahí es `hcm:hr`, jamás `admin`.
- **OIDC**: la **unión** con la lista heredada. Nadie pierde una cadena que ya leía.

Sin concesiones **no se emite la clave `roles` en absoluto**, así que el token de
quien no tiene nada concedido conserva exactamente su forma anterior.

### Superficie de administración

Misma autenticación que el resto de los endpoints internos
(`X-Internal-API-Key`), y misma costura reemplazable hacia service tokens.

| Endpoint | Qué hace |
|---|---|
| `POST /api/v1/internal/app-roles/grant` | concede `(org, user, app, role)`. **201** si la creó, **200** si ya existía |
| `POST /api/v1/internal/app-roles/revoke` | la retira. `changed: false` si no había nada que retirar |
| `GET /api/v1/internal/app-roles/{organization_id}/{user_id}` | `claim_values` vivos + historial completo, incluidas las revocadas |

- **Idempotente en ambos sentidos.** Un `grant` repetido devuelve el
  `granted_at` **original**: la respuesta a «¿cuándo se le dio acceso a nómina?»
  es la primera vez, no el último reintento. Volver a conceder tras revocar crea
  una fila **nueva** (el historial es el punto).
- **404 si no hay membresía activa** en esa organización — el mismo filtro que
  aplica el resolutor, así que una concesión que nunca alimentaría un token se
  señala en vez de aceptarse en silencio. Un solo mensaje para «no existe la
  org» y «no es miembro», para que la superficie no sirva de sonda.
- **Se valida la forma, no el significado.** `app` y `role` son opacos, pero se
  rechaza un separador dentro de un componente: el claim es `f"{app}:{role}"`, y
  un `app` igual a `"hcm:hr"` emitiría `"hcm:hr:x"` y podría **fabricar** un rol
  que el servidor de recursos sí reconoce.
- **No hay endpoint de borrado**, y no debe haberlo.

> **Alcance:** estos roles **no** gobiernan la puerta del ERP de Crea. Una
> auditoría de SSO resolvió que ese control vive en el `WorkspaceMember` de
> nauta. `hcm:*` autoriza dentro de symbiosis-hcm y nada más.

---

## 6. Pasos de operador

1. **Aplicar la migración `015_user_is_service_acct`** deliberadamente contra la
   base de datos objetivo. `promote` **no corre migraciones** en este
   ecosistema. Es aditiva (una columna `NOT NULL DEFAULT false`, nada se altera
   ni se borra) y re-entrante. Hasta aplicarla, el SELECT del ORM falla
   ruidosamente contra una base que no la tiene — el fallo previsto, no una
   respuesta silenciosamente equivocada.
2. **Promover janua.** Sin promote, ningún token nuevo lleva `org_id` y «Mi
   espacio (RH)» sigue en 403.
3. **Desplegar symbiosis-hcm con su cambio hermano ANTES o A LA VEZ.** Este es
   el orden que importa: si `org_id` llega a HCM sin la separación de roles, todo
   `admin` de organización obtiene acceso RH completo. Ver §2.
4. **Verificar** con un token de sesión real que `org_id`, `org_slug` y
   `madfam_org_roles` están presentes, y que `roles` **no** lleva roles de
   organización.
5. **Marcar el login técnico** de crea-map como service principal, cuando ese
   camino se ejecute (ver el handoff del PR).
6. **Aplicar la migración `016_org_member_app_roles` A MANO** antes de promover
   el cambio de roles de aplicación (§5). `promote` **no corre migraciones**: el
   SQL exacto va en el cuerpo del PR. Es aditiva (una tabla nueva y dos índices;
   nada se altera ni se borra) y re-entrante. Hasta aplicarla, el resolutor
   degrada **fail-closed** —no sella ningún rol de aplicación, que es el
   comportamiento de hoy— y los endpoints de concesión fallan ruidosamente
   contra la relación ausente.
7. **Conceder los roles de aplicación** que hagan falta, ya con la tabla puesta:
   para la Dirección de CTM, `hcm:hr` en la organización de Crea. Sin este paso
   la tabla está vacía y **nada cambia para nadie** — que es justamente lo que
   hace seguro promover el código antes de decidir las concesiones.
8. **Verificar** en un token real que `roles` trae `hcm:hr` y que
   `madfam_org_roles` sigue trayendo el rol de organización por separado.

## 7. Referencias

- `apps/api/app/services/org_claims_service.py` — el resolvedor, fuente única
- `apps/api/app/models/app_role.py` — la tabla de concesiones (§5)
- `apps/api/app/routers/v1/internal_app_roles.py` — conceder / revocar / listar
- `apps/api/alembic/versions/016_org_member_app_roles.py` — la migración de §5
- `apps/api/tests/unit/services/test_app_role_claims.py`
- `apps/api/tests/unit/routers/test_internal_app_roles.py`
- `apps/api/app/services/service_principal.py` — el predicado y el claim
- `apps/api/alembic/versions/015_user_is_service_account.py` — la migración
- `apps/api/tests/unit/services/test_org_claims_service.py`
- `apps/api/tests/unit/services/test_service_principal.py`
- `symbiosis-hcm/apps/api/core/roles.py` — el otro lado de §2
- ADR-003 (multi-tenancy), ADR-004 (capability links), `docs/service-tokens.md`
