"""`GET /policies/roles` was permanently shadowed by `GET /policies/{policy_id}`.

Starlette matches routes in declaration order and dispatches to the FIRST full
match. `/{policy_id}` matches any single path segment, so while it was declared
above `/roles`, every request for `/api/v1/policies/roles` was routed into
`get_policy` with `policy_id="roles"`. The roles handler had never run once
since it was written; the endpoint 500'd in production on 2026-08-13.

A route-registration test does not catch this. Both routes were registered, both
appeared in the OpenAPI schema, and `len(router.routes)` was correct the entire
time. Only resolving a path to a *handler* exposes the shadowing, so that is
what these assert.
"""

import ast
import inspect

from starlette.routing import Match

from app.models import Role
from app.routers.v1 import policies
from app.routers.v1.policies import list_roles, router


def _resolve(method: str, path: str):
    """Return the route Starlette would dispatch to, mirroring real routing."""
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "path_params": {},
        "root_path": "",
        "headers": [],
    }
    for route in router.routes:
        match, _ = route.matches(scope)
        if match == Match.FULL:
            return route
    return None


def _executable_source(func) -> str:
    """Source of `func` with its docstring stripped, so prose can't satisfy a scan."""
    tree = ast.parse(inspect.getsource(func))
    node = tree.body[0]
    if ast.get_docstring(node):
        node.body = node.body[1:]
    return ast.unparse(node)


def test_get_roles_resolves_to_the_roles_handler():
    """The regression: this resolved to `get_policy` with policy_id='roles'."""
    resolved = _resolve("GET", "/v1/policies/roles")

    assert resolved is not None, "/v1/policies/roles does not resolve at all"
    assert resolved.endpoint is list_roles, (
        f"/v1/policies/roles resolves to {resolved.endpoint.__name__!r} "
        f"(path {resolved.path!r}), not list_roles. A parametric route is "
        "declared above the literal /roles route and is swallowing it."
    )


def test_no_literal_route_is_shadowed_by_a_parametric_one():
    """Every literal path in this router must reach its own handler.

    Guards future additions: a new `/policies/<name>` route declared below the
    `/{policy_id}` block would be dead on arrival, exactly as `/roles` was.
    """
    for route in router.routes:
        if "{" in route.path:
            continue  # parametric routes are not shadowing targets
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            resolved = _resolve(method, route.path)
            assert resolved is route, (
                f"{method} {route.path} resolves to "
                f"{resolved.endpoint.__name__ if resolved else None!r} instead of "
                f"{route.endpoint.__name__!r}. Move this literal route above the "
                "parametric routes that shadow it."
            )


def test_parametric_policy_routes_are_declared_last():
    """The structural invariant that keeps the above true."""
    paths = [route.path for route in router.routes]
    first_parametric = next(i for i, p in enumerate(paths) if p == "/v1/policies/{policy_id}")
    literal_after = [p for p in paths[first_parametric:] if "{" not in p]

    assert not literal_after, (
        f"Literal routes {literal_after} are declared after /{{policy_id}} and "
        "are therefore unreachable."
    )


def test_roles_are_scoped_by_a_column_that_exists():
    """The second half of the prod 500: `Role.tenant_id` never existed.

    Un-shadowing the route alone would have swapped one AttributeError 500 for
    another, so the scoping column is asserted too.
    """
    assert hasattr(Role, "organization_id")
    assert not hasattr(Role, "tenant_id"), (
        "If a tenant_id column is ever added to roles, revisit list_roles — it "
        "currently scopes through organization membership."
    )

    code = _executable_source(policies.list_roles)
    assert "Role.tenant_id" not in code
    assert "Role.organization_id" in code
