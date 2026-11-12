from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Har API error ka ek hi format:
    {
        "success": false,
        "status_code": 400,
        "errors": {...}
    }
    Frontend (React) mein error handling aasaan ho jaati hai.
    """
    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            "success": False,
            "status_code": response.status_code,
            "errors": response.data,
        }

    return response