from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """?page=2&page_size=6 (default 12, max 50)."""

    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 50