"""Detection layer: fingerprint → platform → report_type → schema_version."""
from app.services.detection.fingerprinter import fingerprint_file, FileFingerprint
from app.services.detection.platform_detector import detect_platform, PlatformDetectionResult
from app.services.detection.report_type_detector import detect_report_type, ReportTypeResult
from app.services.detection.schema_detector import detect_schema_version, SchemaDriftAlert

__all__ = [
    "fingerprint_file", "FileFingerprint",
    "detect_platform", "PlatformDetectionResult",
    "detect_report_type", "ReportTypeResult",
    "detect_schema_version", "SchemaDriftAlert",
]
