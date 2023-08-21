"""Firstuser API views."""
import logging
import string
import random
from typing import Dict, List, Any
from fastapi import APIRouter, Request, Body, Depends, HTTPException

from rasenmaeher_api.web.api.firstuser.schema import (
    FirstuserIsActiveOut,
    FirstuserCheckCodeIn,
    FirstuserCheckCodeOut,
    FirstuserDisableIn,
    FirstuserDisableOut,
    FirstuserEnableIn,
    FirstuserEnableOut,
    FirstuserAddAdminIn,
    FirstuserAddAdminOut,
    FirstuserDeleteAdminIn,
    FirstuserDeleteAdminOut,
    FirstuserListAdminIn,
    FirstuserListAdminOut,
)

from ....settings import settings
from ....sqlitedatabase import sqlite


router = APIRouter()
LOGGER = logging.getLogger(__name__)


async def check_if_api_is_active() -> bool:
    """
    Simple function to check if the api is enabled or not.
    """
    # Get special_rules='first-user from managment
    _q = settings.sqlite_sel_from_management_where_special_rule_like.format(special_rules="first-user")
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_sssfmwsrl1"
        LOGGER.error("{}".format(_reason))
        raise HTTPException(status_code=500, detail=_reason)

    if len(_result) > 0:
        return True

    return False


# /is-active
@router.get("/is-active", response_model=FirstuserIsActiveOut)
async def get_is_active() -> FirstuserIsActiveOut:
    """
    /is-active, basically this one just checks if there is a row with special_rules='first-user' in management table.
    If not, then this API is deemed to be "disabled"...
    """
    _success: bool = True
    _api_active = await check_if_api_is_active()
    if _api_active:
        return FirstuserIsActiveOut(api_is_active=True, success=_success, reason="")

    return FirstuserIsActiveOut(api_is_active=False, success=_success, reason="/firstuser API is disabled")


# /check-code
@router.get("/check-code", response_model=FirstuserCheckCodeOut)
async def get_check_code(
    request: Request,
    params: FirstuserCheckCodeIn = Depends(),
) -> FirstuserCheckCodeOut:
    """
    /check-code?temp_admin_code=xxxx,
    Checks if the given code can be used or not in this /firstuser api route...
    """
    _success: bool = True
    _api_active = await check_if_api_is_active()

    if _api_active is False:
        _reason = "/firstuser API is disabled"
        raise HTTPException(status_code=410, detail=_reason)

    _q = settings.sqlite_sel_from_management_where_special_rule_like.format(special_rules="first-user")
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error q_sssfmwsrl2"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    for _first_user in _result:
        if _first_user[0] == params.temp_admin_code:
            return FirstuserCheckCodeOut(code_ok=True, success=True, reason="")

    return FirstuserCheckCodeOut(code_ok=False, success=True, reason="")


# /disable
@router.post("/disable", response_model=FirstuserDisableOut)
async def post_disable(
    request: Request,
    request_in: FirstuserDisableIn = Body(
        None,
        examples=[FirstuserDisableIn.Config.schema_extra["examples"]],
    ),
) -> FirstuserDisableOut:
    """
    This one disables the /firstuser API route. permit_str aka "admin hash" is required.
    Cannot be done with temp_admin_code.
    """
    _success: bool = True
    _api_active = await check_if_api_is_active()

    if _api_active is False:
        _reason = "/firstuser API is disabled"
        raise HTTPException(status_code=410, detail=_reason)

    # Check that the permit_str is found from management table
    _q = settings.sqlite_sel_from_management.format(management_hash=request_in.permit_str)
    _success, _result = sqlite.run_command(_q)
    if _success is False:
        _reason = "Error. Undefined backend error sssfm2"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    if len(_result) == 0:
        _reason = "Error. Given permit_str doesnt have permissions to disable this api."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=403, detail=_reason)

    _q = settings.sqlite_sel_from_management_where_special_rule_like.format(special_rules="first-user")
    _success, _result = sqlite.run_command(_q)
    if _success is False:
        _reason = "Error. Undefined backend error sssfmwsrl3"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    # Delete the rule from management table where special_rules value is 'first-user'
    _q = settings.sqlite_update_from_management_where_special_rule_like.format(
        special_rules="first-user", new_special_rules=_result[0][1].replace("first-user", "fu-disabled")
    )
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error ssdfmwsrl1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    return FirstuserDisableOut(api_disabled=True, success=True, reason="")


# /enable
@router.post("/enable", response_model=FirstuserEnableOut)
async def post_enable(
    request: Request,
    request_in: FirstuserEnableIn = Body(
        None,
        examples=[FirstuserEnableIn.Config.schema_extra["examples"]],
    ),
) -> FirstuserEnableOut:
    """
    This one enables the /firstuser API route. permit_str aka "admin hash" is required.
    Cannot be done with temp_admin_code. This was mainly added because pytests kind a needs it.
    """
    _success: bool = True
    _api_active = await check_if_api_is_active()

    if _api_active is True:
        _reason = "/firstuser API already enabled"
        return FirstuserEnableOut(api_enabled=True, success=False, reason="API already enabled")

    # Check that the permit_str is found from management table
    _q = settings.sqlite_sel_from_management.format(management_hash=request_in.permit_str)
    _success, _result = sqlite.run_command(_q)
    if _success is False:
        _reason = "Error. Undefined backend error sssfm2"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    LOGGER.info("::: {} :::::::: {}".format(_result, request_in.permit_str))
    if len(_result) == 0:
        _reason = "Error. Given permit_str doesnt have permissions to disable this api."
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=403, detail=_reason)

    _q = settings.sqlite_sel_from_management_where_special_rule_like.format(special_rules="fu-disabled")
    _success, _result = sqlite.run_command(_q)
    if _success is False:
        _reason = "Error. Undefined backend error sssfmwsrl4"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    # Delete the rule from management table where special_rules value is 'first-user'
    _q = settings.sqlite_update_from_management_where_special_rule_like.format(
        special_rules="fu-disabled", new_special_rules=_result[0][1].replace("fu-disabled", "first-user")
    )
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error ssdfmwsrl1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    return FirstuserEnableOut(api_enabled=True, success=True, reason="")


# /add-admin
@router.post("/add-admin", response_model=FirstuserAddAdminOut)
async def post_admin_add(
    request: Request,
    request_in: FirstuserAddAdminIn = Body(
        None,
        examples=[FirstuserAddAdminIn.Config.schema_extra["examples"]],
    ),
) -> FirstuserAddAdminOut:
    """
    Add work_id aka username/identity. This work_id is also elevated to have managing permissions.
    """
    _success: bool = True
    _api_active = await check_if_api_is_active()
    if _api_active is False:
        _reason = "/firstuser API is disabled"
        raise HTTPException(status_code=410, detail=_reason)

    _q = settings.sqlite_sel_from_management_where_special_rule_like.format(special_rules="first-user")
    _success, _result = sqlite.run_command(_q)

    _admin_found: bool = False
    for _first_user in _result:
        if _first_user[0] == request_in.temp_admin_code:
            _admin_found = True

    if _admin_found is False:
        _reason = "Given 'temp_admin_code' has no permission to add new admins."
        raise HTTPException(status_code=403, detail=_reason)

    _work_id_hash = "".join(
        # [B311:blacklist] Standard pseudo-random generators are not suitable for security/cryptographic purposes.
        [
            random.choice(string.ascii_lowercase + string.digits)  # nosec B311 - pseudo-random is good enough
            for n in range(64)
        ]
    )

    _q = settings.sqlite_insert_into_enrollment.format(
        work_id=request_in.work_id,
        work_id_hash=_work_id_hash,
        state="init",
        accepted="yes",
        cert_dl_link="na",
        cert_howto_dl_link="na",
        mtls_test_link="na",
        verification_code="na",
        locked="",
    )
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error ssiie2"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    _q = settings.sqlite_insert_into_management.format(management_hash=_work_id_hash, special_rules="user-admin")
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error ssiim1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    return FirstuserAddAdminOut(admin_added=True, success=True, reason="")


# /delete-admin
@router.post("/delete-admin", response_model=FirstuserDeleteAdminOut)
async def post_delete_admin(
    request: Request,
    request_in: FirstuserDeleteAdminIn = Body(
        None,
        examples=[FirstuserDeleteAdminIn.Config.schema_extra["examples"]],
    ),
) -> FirstuserDeleteAdminOut:
    """
    Remove work_id aka username/identity. The work_id's management hash is also removed from management table.
    """

    _success: bool = True
    _api_active = await check_if_api_is_active()
    if _api_active is False:
        _reason = "/firstuser API is disabled"
        raise HTTPException(status_code=410, detail=_reason)

    _q = settings.sqlite_sel_from_management_where_special_rule_like.format(special_rules="first-user")
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error sssfmwsrl6"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    _admin_found: bool = False
    for _first_user in _result:
        LOGGER.info("{} :::: {}".format(_first_user, request_in.temp_admin_code))
        if _first_user[0] == request_in.temp_admin_code:
            _admin_found = True

    if _admin_found is False:
        _reason = "Given 'temp_admin_code' has no permission to add new admins."
        raise HTTPException(status_code=403, detail=_reason)

    # Get the hash for the work_id
    _q = settings.sqlite_sel_from_enrollment.format(
        work_id=request_in.work_id,
    )
    _success, _result = sqlite.run_command(_q)

    if len(_result) == 0 or _success is False:
        if _success is False:
            _reason = "Error. Undefined backend error sssfe1"
            raise HTTPException(status_code=500, detail=_reason)

        _reason = "No user found with given id."
        raise HTTPException(status_code=404, detail=_reason)

    _work_id_hash: str = _result[0][1]

    _q = settings.sqlite_del_from_management_where_hash.format(management_hash=_work_id_hash)
    _success, _result = sqlite.run_command(_q)
    if _success is False:
        _reason = "Error. Undefined backend error ssdfmwh1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    _q = settings.sqlite_del_from_enrollment_where_hash.format(work_id_hash=_work_id_hash)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error ssdfewh1"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    return FirstuserDeleteAdminOut(admin_removed=True, success=True, reason="")


# /list-admin
@router.get("/list-admin", response_model=FirstuserListAdminOut)
async def get_list_admin(
    request: Request,
    params: FirstuserListAdminIn = Depends(),
) -> FirstuserListAdminOut:
    """
    Return available 'admin' id's and hashes.
    """
    _success: bool = True
    _api_active = await check_if_api_is_active()
    if _api_active is False:
        _reason = "/firstuser API is disabled"
        raise HTTPException(status_code=410, detail=_reason)

    _q = settings.sqlite_sel_from_management_where_special_rule_like.format(special_rules="first-user")
    _success, _result = sqlite.run_command(_q)

    _admin_found: bool = False
    for _first_user in _result:
        LOGGER.info("{} :::: {}".format(_first_user, params.temp_admin_code))
        if _first_user[0] == params.temp_admin_code:
            _admin_found = True

    if _admin_found is False:
        _reason = "Given 'temp_admin_code' has no permission to add new admins."
        raise HTTPException(status_code=403, detail=_reason)

    _q = settings.sqlite_sel_from_management_where_special_rule_like.format(special_rules="user-admin")
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Error. Undefined backend error sssfmwsrl2"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=500, detail=_reason)

    if len(_result) == 0:
        _reason = "No users found..."
        raise HTTPException(status_code=404, detail=_reason)

    _return_list: List[Dict[Any, Any]] = []
    for _manager in _result:
        _q = settings.sqlite_sel_from_enrollment_where_hash.format(work_id_hash=_manager[0])
        _success2, _result2 = sqlite.run_command(_q)
        if _success2 is False:
            _reason = "Error. Undefined backend error sssfewh1"
            LOGGER.error("{} : {}".format(request.url, _reason))
            raise HTTPException(status_code=500, detail=_reason)

        _return_list.append({"work_id": _result2[0][0], "work_id_hash": _result2[0][1]})

    return FirstuserListAdminOut(admin_list=_return_list, success=True, reason="")