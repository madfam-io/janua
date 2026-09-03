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
| `is_service_account` | `true` | **solo** si la identidad es técnica | ver §5 |

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

Si tu servicio necesita roles de **aplicación**, pídelos a tu propia autoridad.
`madfam_org_roles` describe autoridad sobre la **cuenta de janua** y no debe
autorizar nada dentro de un producto. symbiosis-hcm ya hace exactamente esto
(`apps/api/core/roles.py`).

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
  (por defecto `false`) y lo devuelve.

### La regla del provisioning

`provision` **honra la bandera solo al crear**. Una fila existente se devuelve
intacta —igual que ya pasaba con el nombre—: cambiar una identidad viva entre
«persona» y «servicio» tiene consecuencias visibles en rosters y en firmas de
documentos, y no debe ocurrir como efecto secundario del reintento de una app
de roster. La respuesta echa el valor **almacenado**, para que quien llame
detecte el caso sin una segunda lectura.

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

## 5. Pasos de operador

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

## 6. Referencias

- `apps/api/app/services/org_claims_service.py` — el resolvedor, fuente única
- `apps/api/app/services/service_principal.py` — el predicado y el claim
- `apps/api/alembic/versions/015_user_is_service_account.py` — la migración
- `apps/api/tests/unit/services/test_org_claims_service.py`
- `apps/api/tests/unit/services/test_service_principal.py`
- `symbiosis-hcm/apps/api/core/roles.py` — el otro lado de §2
- ADR-003 (multi-tenancy), ADR-004 (capability links), `docs/service-tokens.md`
