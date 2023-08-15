"""Schema for enrollment."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from ....settings import settings


class EnrollmentConfigGenVerifiIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema in"""

    service_management_hash: str
    work_id: Optional[str]
    work_id_hash: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "examples": [
                {
                    "name": "normal",
                    "summary": "Description text",
                    "description": "This containts **description** of values.",
                    "value": {
                        "service_management_hash": "[str] - Hash string having permissions to accept work_id_hash",
                        "work_id": "[str] User defined username/id/workname",
                        "work_id_hash": "[str] Generated hash for work-id",
                    },
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {
                        "service_management_hash": f"{settings.sqlite_init_management_hash}",
                        "work_id": "kissa",
                    },
                },
                {
                    "name": "with_values2",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {
                        "service_management_hash": f"{settings.sqlite_init_management_hash}",
                        "work_id_hash": "kissa123",
                    },
                },
            ]
        }


class EnrollmentConfigGenVerifiOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema out"""

    verification_code: str
    success: bool
    reason: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "example": {
                "verification_code": "[str] Generated verification code for enrollment.",
                "success": "[bool] - Task completed succesfully/failed",
                "reason": "[opt][str] - Usually contiains some info why task might have failed",
            }
        }


class EnrollmentConfigSetStateIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema in"""

    management_hash: str
    state: str
    work_id: Optional[str]
    work_id_hash: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "examples": [
                {
                    "name": "normal",
                    "summary": "Description text",
                    "description": "This containts **description** of values.",
                    "value": {
                        "management_hash": "[str] - Hash string having permissions to accept work_id_hash",
                        "state": "[str] - Current state of enrollment",
                        "work_id": "[str] User defined username/id/workname",
                        "work_id_hash": "[str]",
                    },
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {
                        "management_hash": f"{settings.sqlite_init_management_hash}",
                        "state": "somestate",
                        "work_id": "kissa",
                    },
                },
                {
                    "name": "with_values2",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {
                        "management_hash": f"{settings.sqlite_init_management_hash}",
                        "state": "somestate",
                        "work_id_hash": "kissa123",
                    },
                },
            ]
        }


class EnrollmentConfigSetStateOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema out"""

    success: bool
    reason: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "example": {
                "success": "[bool] - Task completed succesfully/failed",
                "reason": "[opt][str] - Usually contiains some info why task might have failed",
            }
        }


class EnrollmentConfigSetMtlsIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config set mtls schema in"""

    management_hash: str
    mtls_test_link: str
    set_for_all: bool
    work_id: Optional[str]
    work_id_hash: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "examples": [
                {
                    "name": "normal",
                    "summary": "Description text",
                    "description": "This containts **description** of values.",
                    "value": {
                        "management_hash": "[str] - Hash string having permissions to accept work_id_hash",
                        "mtls_test_link": "[str] - Link where mtls can be tested",
                        "set_for_all": "[bool] - Set mtls test link for everyone?",
                        "work_id": "[str]",
                        "work_id_hash": "[str]",
                    },
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {
                        "management_hash": f"{settings.sqlite_init_management_hash}",
                        "mtls_test_link": "https://kuvaton.com/kissa123.jpg",
                        "set_for_all": False,
                        "work_id": "kissa",
                    },
                },
                {
                    "name": "with_values2",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {
                        "management_hash": f"{settings.sqlite_init_management_hash}",
                        "mtls_test_link": "https://kuvaton.com/kissa123.jpg",
                        "set_for_all": True,
                    },
                },
            ]
        }


class EnrollmentConfigSetMtlsOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add mtls schema out"""

    success: bool
    reason: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "example": {
                "success": "[bool] - Task completed succesfully/failed",
                "reason": "[opt][str] - Usually contiains some info why task might have failed",
            }
        }


class EnrollmentConfigSetDLIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema in"""

    management_hash: str
    cert_download_link: Optional[str]
    howto_download_link: Optional[str]
    work_id: Optional[str]
    work_id_hash: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "examples": [
                {
                    "name": "normal",
                    "summary": "Description text",
                    "description": "This containts **description** of values.",
                    "value": {
                        "management_hash": "[str] - Hash string having permissions to accept work_id_hash",
                        "cert_download_link": "[str] - Link where certificate package can be downloaded",
                        "howto_download_link": "[str] - Link where howto info can be downloaded",
                        "work_id": "[str] User defined username/id/workname",
                        "work_id_hash": "[str]",
                    },
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {
                        "management_hash": f"{settings.sqlite_init_management_hash}",
                        "cert_download_link": "https://kuvaton.com/kissa123.jpg",
                        "howto_download_link": "https://kuvaton.com/kissa123.jpg",
                        "work_id": "kissa",
                    },
                },
                {
                    "name": "with_values2",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {
                        "management_hash": f"{settings.sqlite_init_management_hash}",
                        "cert_download_link": "https://kuvaton.com/kissa123.jpg",
                        "howto_download_link": "https://kuvaton.com/kissa123.jpg",
                        "work_id_hash": "kissa123",
                    },
                },
            ]
        }


class EnrollmentConfigSetDLOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema out"""

    success: bool
    reason: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "example": {
                "success": "[bool] - Task completed succesfully/failed",
                "reason": "[opt][str] - Usually contiains some info why task might have failed",
            }
        }


class EnrollmentConfigAddManagerIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema in"""

    management_hash: str
    new_permit_hash: str
    permissions_str: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "examples": [
                {
                    "name": "normal",
                    "summary": "Description text",
                    "description": "This containts **description** of values.",
                    "value": {
                        "management_hash": "[str] - Hash string having permissions to accept work_id_hash",
                        "new_permit_hash": "[str] - Hash string for new 'management_hash'",
                        "permission_str": "[str] - Extra permission for new management_hash.",
                    },
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {
                        "management_hash": f"{settings.sqlite_init_management_hash}",
                        "new_permit_hash": "asdQWEasd2" * 7,  # pragma: allowlist secret
                        "permission_str": "[str] - Extra permission for new management_hash.",
                    },
                },
            ]
        }


class EnrollmentConfigAddManagerOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema out"""

    success: bool
    reason: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "example": {
                "success": "[bool] - Task completed succesfully/failed",
                "reason": "[opt][str] - Usually contiains some info why task might have failed",
            }
        }


class EnrollmentStatusOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment status check schema"""

    status: str
    work_id: str
    work_id_hash: str
    success: bool
    reason: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "example": {
                "state": "[str] - Current state of enrollment",
                "work_id": "[str] User defined username/id/workname",
                "work_id_hash": "[str] - Hash generated for work_id",
                "success": "[bool] - Task completed succesfully/failed",
                "reason": "[opt][str] - Usually contiains some info why task might have failed",
            }
        }


class EnrollmentInitIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init in response schema"""

    work_id: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "examples": [
                {
                    "name": "normal",
                    "summary": "Description text",
                    "description": "This containts **description** of values.",
                    "value": {"work_id": "[str] - Plain text enrollment role id"},
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {"work_id": "taikaponi"},
                },
            ]
        }


class EnrollmentInitOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    work_id: str
    work_id_hash: str
    success: bool
    reason: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "example": {
                "work_id": "[str] User defined username/id/workname",
                "work_id_hash": "[str] - Hash string for work_id",
                "success": "[bool] - Task completed succesfully/failed",
                "reason": "[opt][str] - Usually contiains some info why task might have failed",
            }
        }


class EnrollmentDeliverOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    work_id: str
    work_id_hash: str
    cert_download_link: str
    howto_download_link: str
    mtls_test_link: str
    success: bool
    reason: Optional[str]
    state: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "example": {
                "work_id": "[str] User defined username/id/workname",
                "work_id_hash": "[str] - Hash string for work_id",
                "cert_download_link": "[str] - Link where certificate package can be downloaded",
                "howto_download_link": "[str] - Link where certificate install howto can be downloaded",
                "mtls_test_link": "[str] - Link that can be used to test mtls connection",
                "success": "[bool] - Task completed succesfully/failed",
                "reason": "[opt][str] - Usually contiains some info why task might have failed",
                "state": "[str] - Current state of enrollment",
            }
        }


class EnrollmentAcceptIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    work_id_hash: str
    management_hash: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "examples": [
                {
                    "name": "normal",
                    "summary": "Description text",
                    "description": "This contains **description** of values.",
                    "value": {
                        "work_id_hash": "[str] - Enrollment hash string.",
                        "management_hash": "[str] - Hash string having permissions to accept work_id_hash",
                    },
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** values.",
                    "value": {
                        "work_id_hash": "kissa123",
                        "management_hash": f"{settings.sqlite_init_management_hash}",
                    },
                },
            ]
        }


class EnrollmentAcceptOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    work_id: str
    work_id_hash: str
    management_hash: str
    success: bool
    reason: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "example": {
                "work_id": "[str] User defined username/id/workname",
                "work_id_hash": "[str] - Hash string for work_id",
                "management_hash": "[str] - Hash string used to accept enrollment",
                "success": "[bool] - Task completed succesfully/failed",
                "reason": "[opt][str] - Usually contiains some info why task might have failed",
            }
        }


class EnrollmentListOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    success: bool
    reason: Optional[str]
    work_id_list: List[Dict[Any, Any]]
