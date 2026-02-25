from typing import Any

from fastapi.responses import JSONResponse


def success_response(
    data: Any = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response: dict[str, Any] = {"success": True, "data": data, "error": None}
    if meta is not None:
        response["meta"] = meta
    return response


def error_response(
    error_code: str,
    message: str,
    status_code: int = 400,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "data": None,
            "error": {"code": error_code, "message": message},
        },
    )


def paginated_response(
    data: Any,
    total: int,
    page: int,
    limit: int,
) -> dict[str, Any]:
    return {
        "success": True,
        "data": data,
        "error": None,
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
        },
    }
