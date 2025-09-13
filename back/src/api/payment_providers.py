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
    PaystackCredentialsRequest, KorapayCredentialsRequest,
    VerificationResult, PaymentProviderConfigResponse,
    PaymentProviderListResponse, PaymentProviderType,
    PaymentEnvironment
)
from ..models.api import ApiResponse, ApiErrorResponse
from ..database.connection import get_db
from ..dependencies.auth import CurrentUser
from ..services.payment_provider_service import PaymentProviderService
from ..middleware.rate_limit import (
    RateLimiter, get_client_ip, record_login_attempt, get_rate_limit_headers
)
from ..utils.logger import log

router = APIRouter(prefix="/payments", tags=["Payment Providers"])

# Rate limiter for payment provider verification (5 attempts per 5 minutes)
payment_verification_rate_limiter = RateLimiter(max_attempts=5, window_seconds=300)

async def check_payment_verification_rate_limit(request: Request, merchant_id: UUID) -> None:
    """Check rate limit for payment verification endpoints"""
    client_ip = get_client_ip(request)
    merchant_key = f"merchant:{merchant_id}"
    ip_key = f"ip:{client_ip}"

    # Check both merchant and IP-based rate limits
    if (payment_verification_rate_limiter.is_rate_limited(merchant_key) or
        payment_verification_rate_limiter.is_rate_limited(ip_key)):

        reset_time = max(
            payment_verification_rate_limiter.get_reset_time(merchant_key),
            payment_verification_rate_limiter.get_reset_time(ip_key)
        )
        reset_in = int(reset_time - time.time()) if reset_time > time.time() else 0

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many verification attempts. Try again in {reset_in} seconds.",
            headers={
                "Retry-After": str(reset_in),
                "X-RateLimit-Limit": str(payment_verification_rate_limiter.max_attempts),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(reset_time)) if reset_time > 0 else "0"
            }
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
        422: {"model": ApiErrorResponse, "description": "Invalid credentials"}
    },
    summary="Verify Paystack credentials",
    description="Verify Paystack API credentials and store them securely if valid"
)
async def verify_paystack_credentials(
    payload: PaystackCredentialsRequest,
    request: Request,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
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

    log.info("Paystack credential verification requested", extra={
        "merchant_id": str(current_user.merchant_id),
        "environment": payload.environment.value,
        "event_type": "api_payment_provider_verify_request"
    })

    try:
        service = PaymentProviderService(db)
        result = await service.verify_paystack_credentials(
            merchant_id=current_user.merchant_id,
            credentials=payload
        )

        # Record rate limit attempt
        record_payment_verification_attempt(request, current_user.merchant_id)

        if result.success:
            return ApiResponse(
                ok=True,
                data=result,
                message="Paystack credentials verified and stored successfully"
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
                            "environment": payload.environment.value
                        }
                    }
                ).dict()
            )

    except Exception as e:
        log.error("Paystack credential verification error", extra={
            "merchant_id": str(current_user.merchant_id),
            "error": str(e),
            "event_type": "api_payment_provider_verify_error"
        })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Credential verification failed"
        )

@router.post(
    "/verify/korapay",
    response_model=ApiResponse[VerificationResult],
    responses={
        400: {"model": ApiErrorResponse, "description": "Invalid request data"},
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        429: {"model": ApiErrorResponse, "description": "Rate limit exceeded"},
        422: {"model": ApiErrorResponse, "description": "Invalid credentials"}
    },
    summary="Verify Korapay credentials",
    description="Verify Korapay API credentials and store them securely if valid"
)
async def verify_korapay_credentials(
    payload: KorapayCredentialsRequest,
    request: Request,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
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

    log.info("Korapay credential verification requested", extra={
        "merchant_id": str(current_user.merchant_id),
        "environment": payload.environment.value,
        "event_type": "api_payment_provider_verify_request"
    })

    try:
        service = PaymentProviderService(db)
        result = await service.verify_korapay_credentials(
            merchant_id=current_user.merchant_id,
            credentials=payload
        )

        # Record rate limit attempt
        record_payment_verification_attempt(request, current_user.merchant_id)

        if result.success:
            return ApiResponse(
                ok=True,
                data=result,
                message="Korapay credentials verified and stored successfully"
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
                            "environment": payload.environment.value
                        }
                    }
                ).dict()
            )

    except Exception as e:
        log.error("Korapay credential verification error", extra={
            "merchant_id": str(current_user.merchant_id),
            "error": str(e),
            "event_type": "api_payment_provider_verify_error"
        })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Credential verification failed"
        )

@router.get(
    "/providers",
    response_model=ApiResponse[PaymentProviderListResponse],
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"}
    },
    summary="List payment providers",
    description="Get all configured payment providers for the current merchant"
)
async def list_payment_providers(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    List all payment provider configurations for the current merchant.

    **Response**:
    Returns list of all payment provider configurations with their verification status.
    Credentials are not included in the response for security.
    """

    try:
        service = PaymentProviderService(db)
        providers = await service.get_provider_configs(current_user.merchant_id)

        return ApiResponse(
            ok=True,
            data=PaymentProviderListResponse(
                providers=providers,
                total_count=len(providers)
            ),
            message=f"Found {len(providers)} payment provider configurations"
        )

    except Exception as e:
        log.error("Failed to list payment providers", extra={
            "merchant_id": str(current_user.merchant_id),
            "error": str(e),
            "event_type": "api_payment_providers_list_error"
        })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve payment providers"
        )

@router.delete(
    "/providers/{provider_type}",
    response_model=ApiResponse[dict],
    responses={
        401: {"model": ApiErrorResponse, "description": "Unauthorized"},
        404: {"model": ApiErrorResponse, "description": "Provider configuration not found"}
    },
    summary="Delete payment provider",
    description="Remove a payment provider configuration"
)
async def delete_payment_provider(
    provider_type: PaymentProviderType,
    environment: PaymentEnvironment,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)]
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
            environment=environment
        )

        if deleted:
            log.info("Payment provider configuration deleted", extra={
                "merchant_id": str(current_user.merchant_id),
                "provider_type": provider_type.value,
                "environment": environment.value,
                "event_type": "payment_provider_config_deleted"
            })

            return ApiResponse(
                ok=True,
                data={"deleted": True},
                message=f"{provider_type.value.title()} {environment.value} configuration deleted"
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
                            "environment": environment.value
                        }
                    }
                ).dict()
            )

    except Exception as e:
        log.error("Failed to delete payment provider", extra={
            "merchant_id": str(current_user.merchant_id),
            "provider_type": provider_type.value,
            "environment": environment.value,
            "error": str(e),
            "event_type": "api_payment_provider_delete_error"
        })

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete payment provider configuration"
        )