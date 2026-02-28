"""Application middleware."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Extract IP address and User-Agent from the request for audit logging.

    Stores ``ip_address`` and ``user_agent`` on ``request.state`` so
    downstream route handlers can pass them to the audit service
    without parsing headers themselves.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request, extracting client metadata.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler in the chain.

        Returns:
            Response from downstream handler.
        """
        # Prefer X-Forwarded-For (set by reverse proxies / load balancers)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # First IP in the chain is the original client
            ip_address = forwarded_for.split(",")[0].strip()
        else:
            ip_address = request.client.host if request.client else None

        request.state.ip_address = ip_address
        request.state.user_agent = request.headers.get("user-agent")

        return await call_next(request)
