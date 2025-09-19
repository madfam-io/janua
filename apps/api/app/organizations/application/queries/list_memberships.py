"""
List memberships query and handler
"""

from dataclasses import dataclass
from typing import List
from uuid import UUID

from app.models import User
from ..base import Query, QueryHandler, NotFoundError, PermissionError
from ...domain.models.membership import Membership
from ...domain.services.membership_service import MembershipService
from ...infrastructure.repositories.organization_repository import OrganizationRepository


@dataclass
class MembershipWithUser:
    """Membership with user details"""

    membership: Membership
    user: User


@dataclass
class ListMembershipsQuery(Query):
    """Query to list organization memberships"""

    organization_id: UUID
    requester_id: UUID


@dataclass
class ListMembershipsResult:
    """Result of listing memberships"""

    memberships: List[MembershipWithUser]


class ListMembershipsHandler(QueryHandler[ListMembershipsQuery, ListMembershipsResult]):
    """Handler for listing organization memberships"""

    def __init__(self, repository: OrganizationRepository):
        self.repository = repository
        self.membership_service = MembershipService()

    async def handle(self, query: ListMembershipsQuery) -> ListMembershipsResult:
        """Handle listing organization memberships"""

        # Verify organization exists
        organization = await self.repository.find_by_id(query.organization_id)
        if not organization:
            raise NotFoundError("Organization not found")

        # Check if requester has access
        is_owner = organization.is_owner(query.requester_id)
        requester_membership = await self.repository.find_membership(
            query.organization_id,
            query.requester_id
        )

        if not is_owner and not requester_membership:
            raise PermissionError("Not a member of this organization")

        # Get all memberships with user details
        memberships_with_users = await self.repository.list_memberships_with_users(
            query.organization_id
        )

        return ListMembershipsResult(memberships=memberships_with_users)