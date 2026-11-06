from django.conf import settings


def api_config(_request):
    # The API origin is public by nature; the browser uses it only for a
    # non-blocking wake-up request while Django renders the page.
    return {"api_base_url": settings.API_BASE_URL.rstrip("/")}
