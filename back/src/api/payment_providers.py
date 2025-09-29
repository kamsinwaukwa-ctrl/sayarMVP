"""
Payment Provider API endpoints with comprehensive verification
"""

import time
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from typing import Annotated, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.payment_providers import (
    PaystackCredentialsRequest,
    KorapayCredentialsRequest,
    VerificationResult,
    PaymentProviderConfigResponse,
    PaymentProviderListResponse,
    PaymentProviderType,
    PaymentEnvironment,
    BankListResponse,
    AccountResolutionRequest,
    AccountResolutionResponse,
    SubaccountRequest,
    SubaccountResponse,
    SubaccountUpdateRequest,
    SubaccountUpdateResponse,
)
from ..models.api import ApiResponse, ApiErrorResponse
from ..database.connection import get_db
from ..dependencies.auth import CurrentUser
from ..services.payment_provider_service import PaymentProviderService
from ..middleware.rate_limit import (
    RateLimiter,
    get_client_ip,
    record_login_attempt,
    get_rate_limit_headers,
)
from ..utils.logger import log

router = APIRouter(prefix="/payments", tags=["Payment Providers"])

# Rate limiters
payment_verification_rate_limiter = RateLimiter(max_attempts=5, window_seconds=300)
account_resolution_rate_limiter = RateLimiter(max_attempts=10, window_seconds=60)
subaccount_creation_rate_limiter = RateLimiter(max_attempts=3, window_seconds=300)


async def check_payment_verification_rate_limit(
    request: Request, merchant_id: UUID
) -> None:
    """Check rate limit for payment verification endpoints"""
    client_ip = get_client_ip(request)
    merchant_key = f"merchant:{merchant_id}"
    ip_key = f"ip:{client_ip}"

    # Check both merchant and IP-based rate limits
    if payment_verification_rate_limiter.is_rate_limited(
        merchant_key
    ) or payment_verification_rate_limiter.is_rate_limited(ip_key):

        reset_time = max(
            payment_verification_rate_limiter.get_reset_time(merchant_key),
            payment_verification_rate_limiter.get_reset_time(ip_key),
        )
        reset_in = int(reset_time - time.time()) if reset_time > time.time() else 0

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many verification attempts. Try again in {reset_in} seconds.",
            headers={
                "Retry-After": str(reset_in),
                "X-RateLimit-Limit": str(
                    payment_verification_rate_limiter.max_attempts
                ),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(reset_time)) if reset_time > 0 else "0",
            },
        )


def record_payment_verification_attempt(request: Request, merchant_id: UUID) -> None:
    """Record payment verification attempt for rate limiting"""
    client_ip = get_client_ip(request)
    payment_verification_rate_limiter.record_attempt(f"merchant:{merchant_id}")
    payment_verification_rate_limiter.record_attempt(f"ip:{client_ip}")


@router.post(
    "/verify/paystack",
    response_model=ApiResponse[VerificationResult],
    responses={
        400: {"model": ApiErrorResponse, "description": "Invalid request data"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
        422: {"model": ApiErrorResponse, "description": "Invalid credentials"},
    },
    summary="Verify Paystack credentials",
    description="Verify Paystack API credentials and store them securely if valid",
)
async def verify_paystack_credentials(
    payload: PaystackCredentialsRequest,
    request: Request,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Verify and store Paystack payment credentials.

    **Rate Limited**: 5 requests per 5 minutes per merchant

    **Request Body**:
    - **secret_key**: Paystack secret key (starts with 'sk_')
    - **public_key**: Paystack public key (optional, starts with 'pk_')
    - **environment**: 'test' or 'live'

    **Response**:
    Returns verification result with status and stored configuration details.
    """

    # Apply rate limiting
    await check_payment_verification_rate_limit(request, current_user.merchant_id)

    log.info(
        "Paystack credential verification requested",
        extra={
            "merchant_id": str(current_user.merchant_id),
            "environment": payload.environment.value,
            "event_type": "api_payment_provider_verify_request",
        },
    )

    try:
        service = PaymentProviderService(db)
        result = await service.verify_paystack_credentials(
            merchant_id=current_user.merchant_id, credentials=payload
        )

        # Record rate limit attempt
        record_payment_verification_attempt(request, current_user.merchant_id)

        if result.success:
            return ApiResponse(
                ok=True,
                data=result,
                message="Paystack credentials verified and stored successfully",
            )
        else:
            return JSONResponse(
                status_code=422,
                content=ApiErrorResponse(
                    error={
                        "code": "VERIFICATION_FAILED",
                        "message": "Paystack credential verification failed",
                        "details": {
                            "reason": result.error_message or "Invalid credentials",
                            "provider": "paystack",
                            "environment": payload.environment.value,
                        },
                    }
                ).dict(),
            )

    except Exception as e:
        log.error(
            "Paystack credential verification error",
            extra={
                "merchant_id": str(current_user.merchant_id),
                "error": str(e),
                "event_type": "api_payment_provider_verify_error",
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Credential verification failed",
        )


@router.post(
    "/verify/korapay",
    response_model=ApiResponse[VerificationResult],
    responses={
        400: {"model": ApiErrorResponse, "description": "Invalid request data"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
        422: {"model": ApiErrorResponse, "description": "Invalid credentials"},
    },
    summary="Verify Korapay credentials",
    description="Verify Korapay API credentials and store them securely if valid",
)
async def verify_korapay_credentials(
    payload: KorapayCredentialsRequest,
    request: Request,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Verify and store Korapay payment credentials.

    **Rate Limited**: 5 requests per 5 minutes per merchant

    **Request Body**:
    - **public_key**: Korapay public key (starts with 'pk_')
    - **secret_key**: Korapay secret key (starts with 'sk_')
    - **webhook_secret**: Webhook secret for signature verification (optional)
    - **environment**: 'test' or 'live'

    **Response**:
    Returns verification result with status and stored configuration details.
    """

    # Apply rate limiting
    await check_payment_verification_rate_limit(request, current_user.merchant_id)

    log.info(
        "Korapay credential verification requested",
        extra={
            "merchant_id": str(current_user.merchant_id),
            "environment": payload.environment.value,
            "event_type": "api_payment_provider_verify_request",
        },
    )

    try:
        service = PaymentProviderService(db)
        result = await service.verify_korapay_credentials(
            merchant_id=current_user.merchant_id, credentials=payload
        )

        # Record rate limit attempt
        record_payment_verification_attempt(request, current_user.merchant_id)

        if result.success:
            return ApiResponse(
                ok=True,
                data=result,
                message="Korapay credentials verified and stored successfully",
            )
        else:
            return JSONResponse(
                status_code=422,
                content=ApiErrorResponse(
                    error={
                        "code": "VERIFICATION_FAILED",
                        "message": "Korapay credential verification failed",
                        "details": {
                            "reason": result.error_message or "Invalid credentials",
                            "provider": "korapay",
                            "environment": payload.environment.value,
                        },
                    }
                ).dict(),
            )

    except Exception as e:
        log.error(
            "Korapay credential verification error",
            extra={
                "merchant_id": str(current_user.merchant_id),
                "error": str(e),
                "event_type": "api_payment_provider_verify_error",
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Credential verification failed",
        )


@router.get(
    "/providers",
    response_model=ApiResponse[PaymentProviderListResponse],
    responses={401: {"model": ApiErrorResponse, "description": "Unauthorized"}},
    summary="List payment providers",
    description="Get cached payment provider configurations (fast, DB-only)",
)
async def list_payment_providers(
    current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    List all payment provider configurations for the current merchant.

    **Fast Display**: Returns cached subaccount metadata from our DB (no external API calls).
    **Response**: Subaccount details, sync status, last sync time. No credentials exposed.
    """

    try:
        service = PaymentProviderService(db)
        providers = await service.get_provider_configs_simple(current_user.merchant_id)

        return ApiResponse(
            ok=True,
            data=PaymentProviderListResponse(
                providers=providers, total_count=len(providers)
            ),
            message=f"Found {len(providers)} payment provider configurations",
        )

    except Exception as e:
        log.error(
            "Failed to list payment providers",
            extra={
                "merchant_id": str(current_user.merchant_id),
                "error": str(e),
                "event_type": "api_payment_providers_list_error",
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve payment providers",
        )


@router.delete(
    "/providers/{provider_type}",
    response_model=ApiResponse[dict],
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {
            "model": ApiErrorResponse,
            "description": "Provider configuration not found",
        },
    },
    summary="Delete payment provider",
    description="Remove a payment provider configuration",
)
async def delete_payment_provider(
    provider_type: PaymentProviderType,
    environment: PaymentEnvironment,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a payment provider configuration.

    **Path Parameters**:
    - **provider_type**: Payment provider type ('paystack' or 'korapay')

    **Query Parameters**:
    - **environment**: Environment ('test' or 'live')
    """

    try:
        service = PaymentProviderService(db)
        deleted = await service.delete_provider_config(
            merchant_id=current_user.merchant_id,
            provider_type=provider_type,
            environment=environment,
        )

        if deleted:
            log.info(
                "Payment provider configuration deleted",
                extra={
                    "merchant_id": str(current_user.merchant_id),
                    "provider_type": provider_type.value,
                    "environment": environment.value,
                    "event_type": "payment_provider_config_deleted",
                },
            )

            return ApiResponse(
                ok=True,
                data={"deleted": True},
                message=f"{provider_type.value.title()} {environment.value} configuration deleted",
            )
        else:
            return JSONResponse(
                status_code=404,
                content=ApiErrorResponse(
                    error={
                        "code": "PROVIDER_NOT_FOUND",
                        "message": "Payment provider configuration not found",
                        "details": {
                            "provider_type": provider_type.value,
                            "environment": environment.value,
                        },
                    }
                ).dict(),
            )

    except Exception as e:
        log.error(
            "Failed to delete payment provider",
            extra={
                "merchant_id": str(current_user.merchant_id),
                "provider_type": provider_type.value,
                "environment": environment.value,
                "error": str(e),
                "event_type": "api_payment_provider_delete_error",
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete payment provider configuration",
        )


# New endpoints for bank operations


@router.get(
    "/banks",
    response_model=ApiResponse[BankListResponse],
    responses={401: {"model": ApiErrorResponse, "description": "Unauthorized"}},
    summary="List Nigerian banks",
    description="Get list of Nigerian banks from Paystack with caching",
)
async def list_banks(
    current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Get list of Nigerian banks for account setup.

    **Cached**: Results cached for 6 hours to reduce API calls.
    **Response**: List of banks with name and code for dropdown selection.
    """

    try:
        service = PaymentProviderService(db)
        banks_data = await service.get_nigerian_banks()

        return ApiResponse(
            ok=True,
            data=banks_data,
            message=f"Found {banks_data.total_count} Nigerian banks",
        )

    except Exception as e:
        log.error(
            "Failed to fetch banks list",
            extra={
                "merchant_id": str(current_user.merchant_id),
                "error": str(e),
                "event_type": "api_banks_list_error",
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch banks list",
        )


@router.get(
    "/resolve-account",
    response_model=ApiResponse[AccountResolutionResponse],
    responses={
        400: {"model": ApiErrorResponse, "description": "Invalid request data"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
        422: {"model": ApiErrorResponse, "description": "Account resolution failed"},
    },
    summary="Resolve bank account",
    description="Verify bank account number and get account name",
)
async def resolve_account(
    account_number: str,
    bank_code: str,
    request: Request,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Resolve bank account number to get account holder name.

    **Rate Limited**: 10 requests per minute per merchant and IP

    **Query Parameters**:
    - **account_number**: 10-digit Nigerian account number
    - **bank_code**: Bank code from banks list

    **Response**:
    Returns account holder name if account exists and is valid.
    """

    # Validate input
    try:
        request_data = AccountResolutionRequest(
            account_number=account_number, bank_code=bank_code
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}",
        )

    # Apply rate limiting
    client_ip = get_client_ip(request)
    merchant_key = f"merchant:{current_user.merchant_id}"
    ip_key = f"ip:{client_ip}"

    if account_resolution_rate_limiter.is_rate_limited(
        merchant_key
    ) or account_resolution_rate_limiter.is_rate_limited(ip_key):

        reset_time = max(
            account_resolution_rate_limiter.get_reset_time(merchant_key),
            account_resolution_rate_limiter.get_reset_time(ip_key),
        )
        reset_in = int(reset_time - time.time()) if reset_time > time.time() else 0

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many account resolution attempts. Try again in {reset_in} seconds.",
            headers={"Retry-After": str(reset_in)},
        )

    log.info(
        "Account resolution requested",
        extra={
            "merchant_id": str(current_user.merchant_id),
            "bank_code": bank_code,
            "account_last4": account_number[-4:],
            "event_type": "api_account_resolution_request",
        },
    )

    try:
        service = PaymentProviderService(db)
        result = await service.resolve_account(
            account_number=request_data.account_number,
            bank_code=request_data.bank_code,
        )

        # Record rate limit attempt
        account_resolution_rate_limiter.record_attempt(merchant_key)
        account_resolution_rate_limiter.record_attempt(ip_key)

        if result.success:
            return ApiResponse(
                ok=True,
                data=result,
                message="Account resolved successfully",
            )
        else:
            return JSONResponse(
                status_code=422,
                content=ApiErrorResponse(
                    error={
                        "code": "ACCOUNT_RESOLUTION_FAILED",
                        "message": "Account resolution failed",
                        "details": {
                            "reason": result.error_message or "Invalid account details",
                            "bank_code": bank_code,
                            "account_last4": account_number[-4:],
                        },
                    }
                ).dict(),
            )

    except Exception as e:
        log.error(
            "Account resolution error",
            extra={
                "merchant_id": str(current_user.merchant_id),
                "bank_code": bank_code,
                "account_last4": account_number[-4:],
                "error": str(e),
                "event_type": "api_account_resolution_error",
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account resolution failed",
        )


@router.post(
    "/create-subaccount",
    response_model=ApiResponse[SubaccountResponse],
    responses={
        400: {"model": ApiErrorResponse, "description": "Invalid request data"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        409: {"model": ApiErrorResponse, "description": "Subaccount already exists"},
        422: {"model": ApiErrorResponse, "description": "Subaccount creation failed"},
        429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
    },
    summary="Create Paystack subaccount",
    description="Create Paystack subaccount and save configuration",
)
async def create_subaccount(
    payload: SubaccountRequest,
    request: Request,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create Paystack subaccount for merchant payment processing.

    **Rate Limited**: 3 requests per 5 minutes per merchant
    **Idempotent**: Uses merchant_id to prevent duplicate subaccounts

    **Request Body**:
    - **business_name**: Business name for subaccount
    - **bank_code**: Bank code from banks list
    - **account_number**: 10-digit account number
    - **percentage_charge**: Commission percentage (default 2.0%)
    - **settlement_schedule**: Settlement schedule (default 'AUTO')

    **Response**:
    Returns subaccount details and saves configuration to database.
    """

    # Apply rate limiting
    client_ip = get_client_ip(request)
    merchant_key = f"merchant:{current_user.merchant_id}"
    ip_key = f"ip:{client_ip}"

    if subaccount_creation_rate_limiter.is_rate_limited(
        merchant_key
    ) or subaccount_creation_rate_limiter.is_rate_limited(ip_key):

        reset_time = max(
            subaccount_creation_rate_limiter.get_reset_time(merchant_key),
            subaccount_creation_rate_limiter.get_reset_time(ip_key),
        )
        reset_in = int(reset_time - time.time()) if reset_time > time.time() else 0

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many subaccount creation attempts. Try again in {reset_in} seconds.",
            headers={"Retry-After": str(reset_in)},
        )

    log.info(
        "Subaccount creation requested",
        extra={
            "merchant_id": str(current_user.merchant_id),
            "business_name": payload.business_name,
            "bank_code": payload.bank_code,
            "account_last4": payload.account_number[-4:],
            "event_type": "api_subaccount_creation_request",
        },
    )

    try:
        service = PaymentProviderService(db)
        result = await service.create_paystack_subaccount(
            merchant_id=current_user.merchant_id, subaccount_data=payload
        )

        # Record rate limit attempt
        subaccount_creation_rate_limiter.record_attempt(merchant_key)
        subaccount_creation_rate_limiter.record_attempt(ip_key)

        if result.success:
            return ApiResponse(
                ok=True,
                data=result,
                message="Subaccount created and configured successfully",
            )
        else:
            status_code = 409 if "already exists" in (result.error_message or "").lower() else 422

            return JSONResponse(
                status_code=status_code,
                content=ApiErrorResponse(
                    error={
                        "code": "SUBACCOUNT_CREATION_FAILED",
                        "message": "Subaccount creation failed",
                        "details": {
                            "reason": result.error_message or "Failed to create subaccount",
                            "business_name": payload.business_name,
                            "bank_code": payload.bank_code,
                        },
                    }
                ).dict(),
            )

    except Exception as e:
        log.error(
            "Subaccount creation error",
            extra={
                "merchant_id": str(current_user.merchant_id),
                "business_name": payload.business_name,
                "bank_code": payload.bank_code,
                "error": str(e),
                "event_type": "api_subaccount_creation_error",
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Subaccount creation failed",
        )


# New Paystack-first endpoints

@router.patch(
    "/providers/paystack",
    response_model=ApiResponse[SubaccountUpdateResponse],
    responses={
        400: {"model": ApiErrorResponse, "description": "Invalid request data"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "No subaccount found"},
        422: {"model": ApiErrorResponse, "description": "Paystack update failed"},
        429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
    },
    summary="Update Paystack subaccount",
    description="Update subaccount via Paystack API first, then sync our DB",
)
async def update_paystack_subaccount(
    payload: SubaccountUpdateRequest,
    request: Request,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update Paystack subaccount details: Paystack API first, then sync our DB.

    **Paystack-First Strategy**:
    1. Call Paystack PUT /subaccount/:subaccount_code with provided fields
    2. If Paystack succeeds → update our DB with returned data
    3. If Paystack fails → return error, no DB changes
    4. If DB update fails after Paystack success → partial success + outbox retry

    **Rate Limited**: Uses existing payment verification rate limiter

    **Request Body** (all optional for partial update):
    - **business_name**: Business name for subaccount
    - **bank_code**: Bank code from banks list
    - **account_number**: 10-digit account number
    - **percentage_charge**: Commission percentage
    - **settlement_schedule**: Settlement schedule (AUTO/WEEKLY/MONTHLY/MANUAL)

    **Response**: Update result with sync status and partial success handling
    """

    # Apply rate limiting (reuse existing payment verification limiter)
    await check_payment_verification_rate_limit(request, current_user.merchant_id)

    log.info(
        "Paystack subaccount update requested",
        extra={
            "merchant_id": str(current_user.merchant_id),
            "update_fields": list(payload.dict(exclude_unset=True).keys()),
            "event_type": "api_paystack_subaccount_update_request",
        },
    )

    try:
        service = PaymentProviderService(db)
        result = await service.update_paystack_subaccount(
            merchant_id=current_user.merchant_id,
            update_data=payload
        )

        # Record rate limit attempt
        record_payment_verification_attempt(request, current_user.merchant_id)

        if result.success:
            status_code = 200 if not result.partial_success else 202
            return JSONResponse(
                status_code=status_code,
                content=ApiResponse(
                    ok=True,
                    data=result.dict(),
                    message=result.message,
                ).dict()
            )
        else:
            return JSONResponse(
                status_code=422,
                content=ApiErrorResponse(
                    error={
                        "code": "PAYSTACK_UPDATE_FAILED",
                        "message": "Paystack subaccount update failed",
                        "details": {
                            "reason": result.message,
                            "subaccount_code": result.subaccount_code,
                        },
                    }
                ).dict(),
            )

    except ValueError as ve:
        # No subaccount found
        return JSONResponse(
            status_code=404,
            content=ApiErrorResponse(
                error={
                    "code": "SUBACCOUNT_NOT_FOUND",
                    "message": str(ve),
                    "details": {"merchant_id": str(current_user.merchant_id)},
                }
            ).dict(),
        )

    except Exception as e:
        log.error(
            "Paystack subaccount update error",
            extra={
                "merchant_id": str(current_user.merchant_id),
                "error": str(e),
                "event_type": "api_paystack_subaccount_update_error",
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Subaccount update failed",
        )


@router.post(
    "/providers/paystack/sync",
    response_model=ApiResponse[PaymentProviderConfigResponse],
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "No subaccount found"},
        422: {"model": ApiErrorResponse, "description": "Sync failed"},
        429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
    },
    summary="Manual sync with Paystack",
    description="Fetch fresh subaccount data from Paystack and update our DB",
)
async def sync_paystack_subaccount(
    request: Request,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Manual sync: fetch fresh subaccount data from Paystack and update our DB.

    **Used for**: "Sync with Paystack" button in Settings UI

    **Process**:
    1. Call Paystack GET /subaccount/:subaccount_code
    2. Update our DB with latest data from Paystack
    3. Return fresh configuration with updated sync status

    **Rate Limited**: Uses existing payment verification rate limiter
    """

    # Apply rate limiting
    await check_payment_verification_rate_limit(request, current_user.merchant_id)

    log.info(
        "Manual Paystack sync requested",
        extra={
            "merchant_id": str(current_user.merchant_id),
            "event_type": "api_paystack_manual_sync_request",
        },
    )

    try:
        service = PaymentProviderService(db)
        updated_config = await service.sync_paystack_subaccount(current_user.merchant_id)

        # Record rate limit attempt
        record_payment_verification_attempt(request, current_user.merchant_id)

        return ApiResponse(
            ok=True,
            data=updated_config.dict(),
            message="Synced successfully with Paystack",
        )

    except ValueError as ve:
        # No subaccount found
        return JSONResponse(
            status_code=404,
            content=ApiErrorResponse(
                error={
                    "code": "SUBACCOUNT_NOT_FOUND",
                    "message": str(ve),
                    "details": {"merchant_id": str(current_user.merchant_id)},
                }
            ).dict(),
        )

    except Exception as e:
        log.error(
            "Manual Paystack sync error",
            extra={
                "merchant_id": str(current_user.merchant_id),
                "error": str(e),
                "event_type": "api_paystack_manual_sync_error",
            },
        )

        # Check if it's a sync failure vs system error
        if "Sync failed:" in str(e):
            return JSONResponse(
                status_code=422,
                content=ApiErrorResponse(
                    error={
                        "code": "SYNC_FAILED",
                        "message": "Failed to sync with Paystack",
                        "details": {"reason": str(e)},
                    }
                ).dict(),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Manual sync failed",
            )
