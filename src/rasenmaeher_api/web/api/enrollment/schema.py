"""Schema for enrollment."""
from typing import Optional
from pydantic import BaseModel
from ....settings import settings


class EnrollmentConfigSetStateIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema in"""

    permit_str: str
    state: str
    work_id: Optional[str]
    enroll_str: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "examples": [
                {
                    "name": "normal",
                    "summary": "Description text",
                    "description": "This containts **description** of values.",
                    "value": {
                        "permit_str": "[str] - Hash string having permissions to accept enroll_str",
                        "state": "[str] - Current state of enrollment",
                        "work_id": "[str]",
                        "enroll_str": "[str]",
                    },
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {
                        "permit_str": f"{settings.sqlite_init_management_hash}",
                        "state": "somestate",
                        "work_id": "kissa",
                    },
                },
                {
                    "name": "with_values2",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {
                        "permit_str": f"{settings.sqlite_init_management_hash}",
                        "state": "somestate",
                        "enroll_str": "kissa123",
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


class EnrollmentConfigSetDLIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema in"""

    permit_str: str
    download_link: str
    work_id: Optional[str]
    enroll_str: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "examples": [
                {
                    "name": "normal",
                    "summary": "Description text",
                    "description": "This containts **description** of values.",
                    "value": {
                        "permit_str": "[str] - Hash string having permissions to accept enroll_str",
                        "download_link": "[str] - Link where package can be downloaded",
                        "work_id": "[str]",
                        "enroll_str": "[str]",
                    },
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {
                        "permit_str": f"{settings.sqlite_init_management_hash}",
                        "download_link": "https://kuvaton.com/kissa123.jpg",
                        "work_id": "kissa",
                    },
                },
                {
                    "name": "with_values2",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {
                        "permit_str": f"{settings.sqlite_init_management_hash}",
                        "download_link": "https://kuvaton.com/kissa123.jpg",
                        "enroll_str": "kissa123",
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

    permit_str: str
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
                        "permit_str": "[str] - Hash string having permissions to accept enroll_str",
                        "new_permit_hash": "[str] - Hash string for new 'permit_str'",
                        "permission_str": "[str] - Extra permission for new permit_str.",
                    },
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {
                        "permit_str": f"{settings.sqlite_init_management_hash}",
                        "new_permit_hash": "asdQWEasd2" * 7,  # pragma: allowlist secret
                        "permission_str": "[str] - Extra permission for new permit_str.",
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
    success: bool
    reason: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "example": {
                "state": "[str] - Current state of enrollment",
                "work_id": "[str] - Plain text enrollment role id",
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
    enroll_str: str
    success: bool
    reason: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "example": {
                "work_id": "[str] - Plain text enrollment role id",
                "enroll_str": "[str] - Hash string for work_id",
                "success": "[bool] - Task completed succesfully/failed",
                "reason": "[opt][str] - Usually contiains some info why task might have failed",
            }
        }


class EnrollmentDeliverOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    work_id: str
    enroll_str: str
    download_url: str
    success: bool
    reason: Optional[str]
    state: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "example": {
                "work_id": "[str] - Plain text enrollment role id",
                "enroll_str": "[str] - Hash string for work_id",
                "download_url": "[str] - Link where package can be downloaded",
                "success": "[bool] - Task completed succesfully/failed",
                "reason": "[opt][str] - Usually contiains some info why task might have failed",
                "state": "[str] - Current state of enrollment",
            }
        }


class EnrollmentAcceptIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    enroll_str: str
    permit_str: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "examples": [
                {
                    "name": "normal",
                    "summary": "Description text",
                    "description": "This contains **description** of values.",
                    "value": {
                        "enroll_str": "[str] - Enrollment hash string.",
                        "permit_str": "[str] - Hash string having permissions to accept enroll_str",
                    },
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** values.",
                    "value": {
                        "enroll_str": "kissa123",
                        "permit_str": f"{settings.sqlite_init_management_hash}",
                    },
                },
            ]
        }


class EnrollmentAcceptOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    work_id: str
    enroll_str: str
    permit_str: str
    success: bool
    reason: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "example": {
                "work_id": "[str] - Plain text enrollment role id",
                "enroll_str": "[str] - Hash string for work_id",
                "permit_str": "[str] - Hash string used to accept enrollment",
                "success": "[bool] - Task completed succesfully/failed",
                "reason": "[opt][str] - Usually contiains some info why task might have failed",
            }
        }
