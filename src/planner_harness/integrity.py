"""Integrity failures require reconciliation and never count as invalid model prose."""


class IntegrityError(RuntimeError):
    failure_kind = "integrity_error"
