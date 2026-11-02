"""Human approval records — decisions come only from CLI/operator input."""

from __future__ import annotations

import uuid
from pathlib import Path

from agentic_engineer.models.approval import (
    ApprovalDecision,
    ApprovalRecord,
    ApprovalType,
)
from agentic_engineer.models.common import utc_now
from agentic_engineer.persistence.json_store import JsonStore


class ApprovalError(Exception):
    """Invalid approval transition."""


class ApprovalService:
    def __init__(self, workflow_dir: Path) -> None:
        self._store = JsonStore(workflow_dir)
        self._relative = "approvals.json"

    def _load(self) -> list[ApprovalRecord]:
        path = self._store.path_for(self._relative)
        if not path.exists():
            return []
        raw = self._store.read_json(self._relative)
        items = raw.get("approvals", [])
        return [ApprovalRecord.model_validate(item) for item in items]

    def _save(self, records: list[ApprovalRecord]) -> None:
        self._store.write_json(
            self._relative,
            {"approvals": [r.model_dump(mode="json") for r in records]},
        )

    def create_pending(
        self,
        *,
        workflow_id: str,
        approval_type: ApprovalType,
        requested_action: str,
        artifact_ref: str | None = None,
    ) -> ApprovalRecord:
        records = self._load()
        record = ApprovalRecord(
            id=f"appr_{uuid.uuid4().hex[:10]}",
            workflow_id=workflow_id,
            approval_type=approval_type,
            requested_action=requested_action,
            decision=ApprovalDecision.PENDING,
            artifact_ref=artifact_ref,
        )
        records.append(record)
        self._save(records)
        return record

    def get(self, approval_id: str) -> ApprovalRecord | None:
        for record in self._load():
            if record.id == approval_id:
                return record
        return None

    def pending(self) -> list[ApprovalRecord]:
        return [r for r in self._load() if r.decision == ApprovalDecision.PENDING]

    def decide(
        self,
        approval_id: str,
        decision: ApprovalDecision,
        *,
        comment: str | None = None,
    ) -> ApprovalRecord:
        if decision == ApprovalDecision.PENDING:
            raise ApprovalError("Decision must not remain pending")
        records = self._load()
        updated: ApprovalRecord | None = None
        new_records: list[ApprovalRecord] = []
        for record in records:
            if record.id != approval_id:
                new_records.append(record)
                continue
            if record.decision != ApprovalDecision.PENDING:
                raise ApprovalError(f"Approval {approval_id} is already decided")
            updated = record.model_copy(
                update={
                    "decision": decision,
                    "comment": comment,
                    "decided_at": utc_now(),
                }
            )
            new_records.append(updated)
        if updated is None:
            raise ApprovalError(f"Unknown approval id: {approval_id}")
        self._save(new_records)
        return updated
