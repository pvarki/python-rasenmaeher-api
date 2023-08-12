"""Schema for enrollment."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class FirstuserIsActiveOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema out"""

    api_is_active: bool
    success: bool
    reason: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "example": {
                "api_is_active": "[bool] - True = this api (/firstuser) can still be used",
                "success": "[bool] - Task completed succesfully/failed",
                "reason": "[opt][str] - Usually contiains some info why task might have failed",
            }
        }


class FirstuserCheckCodeIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init in response schema"""

    temp_admin_code: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "examples": [
                {
                    "name": "normal",
                    "summary": "Description text",
                    "description": "This containts **description** of values.",
                    "value": {"temp_admin_code": "[str] - temporary init admin users string"},
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {"temp_admin_code": "some_permit_hash_abba_abc"},
                },
            ]
        }


class FirstuserCheckCodeOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema out"""

    code_ok: bool
    success: bool
    reason: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "example": {
                "code_ok": "[bool] - True = Requested 'first use admin code' was found and can be used.",
                "success": "[bool] - Task completed succesfully/failed",
                "reason": "[opt][str] - Usually contiains some info why task might have failed",
            }
        }


class FirstuserDisableIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init in response schema"""

    permit_str: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "examples": [
                {
                    "name": "normal",
                    "summary": "Description text",
                    "description": "This containts **description** of values.",
                    "value": {"permit_str": "[str] - admin users string"},
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {"permit_str": "some_permit_hash_abba_abc"},
                },
            ]
        }


class FirstuserDisableOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema out"""

    api_disabled: bool
    success: bool
    reason: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "example": {
                "api_disabled": "[bool] - True = this api (/firstuser) should be disabled now.",
                "success": "[bool] - Task completed succesfully/failed",
                "reason": "[opt][str] - Usually contiains some info why task might have failed",
            }
        }


class FirstuserAddAdminIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init in response schema"""

    temp_admin_code: str
    work_id: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "examples": [
                {
                    "name": "normal",
                    "summary": "Description text",
                    "description": "This containts **description** of values.",
                    "value": {
                        "temp_admin_code": "[str] - admin users string",
                        "work_id": "[str] - id/name for new user that is elevated to admin",
                    },
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {"temp_admin_code": "first_time_user_secret_or_something", "work_id": "porakoira666"},
                },
            ]
        }


class FirstuserAddAdminOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema out"""

    admin_added: bool
    success: bool
    reason: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "example": {
                "admin_added": "[bool] - True = admin user were added",
                "success": "[bool] - Task completed succesfully/failed",
                "reason": "[opt][str] - Usually contiains some info why task might have failed",
            }
        }


class FirstuserDeleteAdminIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init in response schema"""

    temp_admin_code: str
    work_id: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "examples": [
                {
                    "name": "normal",
                    "summary": "Description text",
                    "description": "This containts **description** of values.",
                    "value": {
                        "temp_admin_code": "[str] - admin users string",
                        "work_id": "[str] - id/name for user that will be deleted",
                    },
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {"temp_admin_code": "first_time_user_secret_or_something", "work_id": "porakoira666"},
                },
            ]
        }


class FirstuserDeleteAdminOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema out"""

    admin_removed: bool
    success: bool
    reason: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "example": {
                "admin_removed": "[bool] - True = admin user were removed",
                "success": "[bool] - Task completed succesfully/failed",
                "reason": "[opt][str] - Usually contiains some info why task might have failed",
            }
        }


class FirstuserListAdminIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init in response schema"""

    temp_admin_code: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "examples": [
                {
                    "name": "normal",
                    "summary": "Description text",
                    "description": "This containts **description** of values.",
                    "value": {"temp_admin_code": "[str] - temporary init admin users string"},
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {"temp_admin_code": "some_permit_hash_abba_abc"},
                },
            ]
        }


class FirstuserListAdminOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema out"""

    admin_list: List[Dict[Any, Any]]
    success: bool
    reason: Optional[str]

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        schema_extra = {
            "example": {
                "admin_list": "list[str] - list of 'admin id's' found...",
                "success": "[bool] - Task completed succesfully/failed",
                "reason": "[opt][str] - Usually contiains some info why task might have failed",
            }
        }
