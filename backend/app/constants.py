from enum import Enum


class Roles(str, Enum):
    ADMIN = "admin"
    PROVINCE_OFFICER = "province_officer"
    DISTRICT_OFFICER = "district_officer"
    COMMUNE_OFFICER = "commune_officer"


class PovertyStatus(str, Enum):
    POOR = "poor"
    NEAR_POOR = "near_poor"
    ESCAPED = "escaped_poverty"
    AT_RISK = "at_risk"


class CollectionStatus(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    SUBMITTED = "submitted"


class PolicyCategory(str, Enum):
    DECREE = "decree"
    CIRCULAR = "circular"
    REPORT = "report"
    GUIDELINE = "guideline"
    NEWS = "news"
    ANNOUNCEMENT = "announcement"


POLICY_SUMMARY_MAX_LENGTH = 300

DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 100
