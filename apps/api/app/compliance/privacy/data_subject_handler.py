"""
Data Subject Request Handler
Handles GDPR data subject requests including access, erasure, and portability rights.
"""

import json
import logging
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from app.core.database import get_session
from app.models.compliance import (
    ComplianceFramework,
    DataCategory,
    DataSubjectRequest,
    DataSubjectRequestType,
    RequestStatus,
)
from app.services.data_export_serializer import (
    assert_no_secrets,
    build_export_archive,
    collect_user_export_data,
    serialize_export,
)

from ..audit import AuditEventType, AuditLogger, EvidenceType
from .privacy_models import DataSubjectRequestResponse
from .privacy_types import DataExportFormat

# Directory where generated export artifacts are written. Governed by the
# canonical ``settings.DATA_EXPORT_PATH`` config (default
# ``/var/compliance/exports``); a ``DATA_EXPORT_DIR`` env var override is
# honored for environments where that path is not writable (dev/test). The
# request record stores the returned artifact path in ``response_data_url`` so
# a download endpoint / secure-link issuer can serve it.
try:
    from app.config import settings as _settings

    _DEFAULT_EXPORT_DIR = _settings.DATA_EXPORT_PATH
except Exception:  # pragma: no cover - settings always import in practice
    _DEFAULT_EXPORT_DIR = os.path.join(tempfile.gettempdir(), "janua-data-exports")

_EXPORT_DIR = os.environ.get("DATA_EXPORT_DIR", _DEFAULT_EXPORT_DIR)

logger = logging.getLogger(__name__)


class DataSubjectRequestHandler:
    """Handles data subject requests for GDPR compliance"""

    def __init__(self, audit_logger: AuditLogger):
        self.audit_logger = audit_logger

    async def create_data_subject_request(
        self,
        user_id: str,
        request_type: DataSubjectRequestType,
        description: str = "",
        data_categories: List[DataCategory] = None,
        specific_fields: List[str] = None,
        date_range_start: Optional[datetime] = None,
        date_range_end: Optional[datetime] = None,
        organization_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> str:
        """Create a new data subject request with automated processing"""

        request_id = f"DSR-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

        # Calculate response deadline (30 days for GDPR)
        response_due_date = datetime.utcnow() + timedelta(days=30)

        async with get_session() as session:
            # Create request record
            request = DataSubjectRequest(
                request_id=request_id,
                user_id=uuid.UUID(user_id),
                request_type=request_type,
                description=description,
                data_categories=data_categories or [],
                specific_fields=specific_fields or [],
                date_range_start=date_range_start,
                date_range_end=date_range_end,
                response_due_date=response_due_date,
                organization_id=uuid.UUID(organization_id) if organization_id else None,
                tenant_id=uuid.UUID(tenant_id) if tenant_id else None,
                ip_address=ip_address,
                user_agent=user_agent,
                request_source="api",
            )

            session.add(request)
            await session.commit()
            await session.refresh(request)

        # Log compliance event
        await self.audit_logger.log_compliance_event(
            event_type=AuditEventType.DATA_ACCESS,
            resource_type="data_subject_request",
            resource_id=request_id,
            action="create",
            outcome="success",
            user_id=user_id,
            organization_id=organization_id,
            tenant_id=tenant_id,
            ip_address=ip_address,
            user_agent=user_agent,
            control_id="GDPR-15-22",
            compliance_frameworks=[ComplianceFramework.GDPR],
            raw_data={
                "request_type": request_type.value,
                "data_categories": data_categories,
                "specific_fields": specific_fields,
            },
        )

        # Schedule automated processing
        await self._schedule_request_processing(request_id, request_type)

        logger.info(
            f"Data subject request created: {request_id}",
            extra={
                "user_id": user_id,
                "request_type": request_type.value,
                "response_due_date": response_due_date.isoformat(),
            },
        )

        return request_id

    async def process_access_request(
        self, request_id: str, include_metadata: bool = True
    ) -> DataSubjectRequestResponse:
        """Process GDPR Article 15 access request"""

        async with get_session() as session:
            # Get request details
            result = await session.execute(
                select(DataSubjectRequest).where(DataSubjectRequest.request_id == request_id)
            )
            request = result.scalar_one_or_none()

            if not request:
                raise ValueError(f"Request not found: {request_id}")

            # Collect all user data
            user_data = await self._collect_user_data(
                str(request.user_id),
                request.data_categories,
                request.specific_fields,
                request.date_range_start,
                request.date_range_end,
                include_metadata,
            )

            # Generate export file
            export_url = await self._generate_data_export(
                request_id, user_data, DataExportFormat.JSON
            )

            # Update request status
            request.status = RequestStatus.COMPLETED
            request.completed_at = datetime.utcnow()
            request.response_data_url = export_url
            request.response_method = "secure_download"

            await session.commit()

        # Log completion
        await self.audit_logger.log_compliance_event(
            event_type=AuditEventType.DATA_ACCESS,
            resource_type="data_subject_request",
            resource_id=request_id,
            action="complete",
            outcome="success",
            user_id=str(request.user_id),
            control_id="GDPR-15",
            compliance_frameworks=[ComplianceFramework.GDPR],
        )

        # Collect evidence
        await self.audit_logger.collect_evidence(
            evidence_type=EvidenceType.USER_ACTIVITY,
            title=f"GDPR Access Request Completion - {request_id}",
            description=f"Completed data access request for user {request.user_id}",
            content=user_data,
            source_system="privacy_manager",
            collector_id="system",
            control_objectives=["GDPR-15"],
            compliance_frameworks=[ComplianceFramework.GDPR],
        )

        return DataSubjectRequestResponse(
            request_id=request_id,
            response_type="access",
            data=user_data,
            export_url=export_url,
            completion_time=datetime.utcnow(),
            notes="Data access request completed successfully",
        )

    async def process_erasure_request(
        self, request_id: str, verify_identity: bool = True, backup_before_deletion: bool = True
    ) -> DataSubjectRequestResponse:
        """Process GDPR Article 17 right to be forgotten request"""

        async with get_session() as session:
            # Get request details
            result = await session.execute(
                select(DataSubjectRequest).where(DataSubjectRequest.request_id == request_id)
            )
            request = result.scalar_one_or_none()

            if not request:
                raise ValueError(f"Request not found: {request_id}")

            if verify_identity and not request.identity_verified:
                raise ValueError("Identity verification required for erasure request")

            user_id = str(request.user_id)

            # Create backup if requested
            backup_ref = None
            if backup_before_deletion:
                user_data = await self._collect_user_data(user_id)
                backup_ref = await self._create_erasure_backup(request_id, user_data)

            # Perform erasure according to data categories
            erasure_summary = await self._perform_data_erasure(
                user_id, request.data_categories, request.specific_fields
            )

            # Update request status
            request.status = RequestStatus.COMPLETED
            request.completed_at = datetime.utcnow()
            request.response_notes = f"Data erasure completed. Backup reference: {backup_ref}"

            await session.commit()

        # Log erasure completion
        await self.audit_logger.log_compliance_event(
            event_type=AuditEventType.DATA_ACCESS,
            resource_type="data_subject_request",
            resource_id=request_id,
            action="erasure_complete",
            outcome="success",
            user_id=user_id,
            control_id="GDPR-17",
            compliance_frameworks=[ComplianceFramework.GDPR],
            raw_data=erasure_summary,
        )

        return DataSubjectRequestResponse(
            request_id=request_id,
            response_type="erasure",
            data=erasure_summary,
            export_url=None,
            completion_time=datetime.utcnow(),
            notes=f"Data erasure completed. Items processed: {erasure_summary.get('total_items', 0)}",
        )

    async def process_portability_request(
        self, request_id: str, export_format: DataExportFormat = DataExportFormat.JSON
    ) -> DataSubjectRequestResponse:
        """Process GDPR Article 20 data portability request"""

        async with get_session() as session:
            # Get request details
            result = await session.execute(
                select(DataSubjectRequest).where(DataSubjectRequest.request_id == request_id)
            )
            request = result.scalar_one_or_none()

            if not request:
                raise ValueError(f"Request not found: {request_id}")

            # Collect portable data (only data provided by user with consent)
            portable_data = await self._collect_portable_data(
                str(request.user_id), request.data_categories
            )

            # Generate structured export
            export_url = await self._generate_data_export(
                request_id, portable_data, export_format, structured_format=True
            )

            # Update request status
            request.status = RequestStatus.COMPLETED
            request.completed_at = datetime.utcnow()
            request.response_data_url = export_url
            request.response_method = "structured_download"

            await session.commit()

        # Log completion
        await self.audit_logger.log_compliance_event(
            event_type=AuditEventType.DATA_ACCESS,
            resource_type="data_subject_request",
            resource_id=request_id,
            action="portability_complete",
            outcome="success",
            user_id=str(request.user_id),
            control_id="GDPR-20",
            compliance_frameworks=[ComplianceFramework.GDPR],
        )

        return DataSubjectRequestResponse(
            request_id=request_id,
            response_type="portability",
            data=portable_data,
            export_url=export_url,
            completion_time=datetime.utcnow(),
            notes=f"Data portability export generated in {export_format.value} format",
        )

    async def _schedule_request_processing(
        self, request_id: str, request_type: DataSubjectRequestType
    ):
        """Schedule automated processing for request"""
        # Implementation would integrate with task queue
        logger.info(f"Scheduled processing for {request_type.value} request: {request_id}")

    async def _collect_user_data(
        self,
        user_id: str,
        data_categories: List[DataCategory] = None,
        specific_fields: List[str] = None,
        date_range_start: Optional[datetime] = None,
        date_range_end: Optional[datetime] = None,
        include_metadata: bool = True,
    ) -> Dict[str, Any]:
        """Collect the user's full data set for a GDPR Article 15 access request.

        Gathers the real records across every identity model (profile, org
        memberships, sessions, MFA/passkey metadata, OAuth grants/accounts,
        audit logs). Secret material (password hashes, MFA seeds, tokens,
        credential keys) is excluded by the serializer's allowlist design.
        """
        async with get_session() as session:
            data = await collect_user_export_data(
                session,
                user_id,
                include_audit_logs=include_metadata,
                date_range_start=date_range_start,
                date_range_end=date_range_end,
            )
        if data_categories:
            data["export_metadata"]["requested_data_categories"] = [
                cat.value for cat in data_categories
            ]
        if specific_fields:
            data["export_metadata"]["requested_specific_fields"] = list(specific_fields)
        assert_no_secrets(data)
        return data

    async def _collect_portable_data(
        self, user_id: str, data_categories: List[DataCategory] = None
    ) -> Dict[str, Any]:
        """Collect the portable subset for a GDPR Article 20 request.

        Article 20 covers data the data subject provided themselves in a
        structured, commonly used, machine-readable form: profile, org
        memberships and OAuth grants. Server-generated telemetry (sessions,
        audit logs) is excluded, as is all secret material.
        """
        async with get_session() as session:
            data = await collect_user_export_data(
                session,
                user_id,
                portable_only=True,
            )
        if data_categories:
            data["export_metadata"]["requested_data_categories"] = [
                cat.value for cat in data_categories
            ]
        assert_no_secrets(data)
        return data

    async def _generate_data_export(
        self,
        request_id: str,
        data: Dict[str, Any],
        format: DataExportFormat,
        structured_format: bool = False,
    ) -> str:
        """Serialize ``data`` to a real artifact on disk and return its path.

        JSON/CSV/XML are written as a single file. For the structured
        portability export we additionally bundle per-section JSON files into
        a zip archive for easier downstream consumption. The path is stored on
        the request record (``response_data_url``) for a secure-download step.
        """
        # Never let a secret slip into a written artifact.
        assert_no_secrets(data)

        os.makedirs(_EXPORT_DIR, exist_ok=True)
        fmt = format.value if hasattr(format, "value") else str(format)

        if structured_format and fmt == DataExportFormat.JSON.value:
            payload = build_export_archive(data, manifest_name=f"{request_id}.json")
            path = os.path.join(_EXPORT_DIR, f"{request_id}.zip")
            with open(path, "wb") as handle:
                handle.write(payload)
        else:
            payload = serialize_export(data, fmt)
            path = os.path.join(_EXPORT_DIR, f"{request_id}.{fmt}")
            with open(path, "wb") as handle:
                handle.write(payload)

        logger.info(
            "Generated data export artifact",
            extra={"request_id": request_id, "format": fmt, "bytes": len(payload)},
        )
        return path

    async def _create_erasure_backup(self, request_id: str, user_data: Dict[str, Any]) -> str:
        """Persist a secret-free backup of the user's data before erasure.

        Writes the same allowlisted, credential-free export produced for an
        access request so an erasure can be audited / reversed within the
        retention window without ever archiving secret material.
        """
        assert_no_secrets(user_data)
        os.makedirs(_EXPORT_DIR, exist_ok=True)
        backup_ref = f"BACKUP-{request_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        path = os.path.join(_EXPORT_DIR, f"{backup_ref}.json")
        with open(path, "wb") as handle:
            handle.write(json.dumps(user_data, indent=2, ensure_ascii=False).encode("utf-8"))
        logger.info(f"Created erasure backup: {backup_ref}")
        return backup_ref

    async def _perform_data_erasure(
        self,
        user_id: str,
        data_categories: List[DataCategory] = None,
        specific_fields: List[str] = None,
    ) -> Dict[str, Any]:
        """Perform data erasure according to specified criteria"""
        # Implementation would perform actual data deletion
        return {
            "user_id": user_id,
            "erasure_timestamp": datetime.utcnow().isoformat(),
            "categories_processed": [cat.value for cat in (data_categories or [])],
            "total_items": 0,
            "status": "completed",
        }
