from django.shortcuts import render


def server_error(request):
    """Show a branded, retryable service screen for unexpected server errors."""
    response = render(request, "server_error.html", status=503)
    response["Retry-After"] = "5"
    response["Cache-Control"] = "no-store"
    return response
