from ninja.pagination import PaginationBase
from ninja import Schema

class CustomPagination(PaginationBase):
    class Input(Schema):
        page: int = 1
        per_page: int = 20

    class Output(Schema):
        count: int
        page: int
        per_page: int
        items: list

    def paginate_queryset(self, queryset, pagination: Input, **params):
        page = pagination.page
        per_page = pagination.per_page
        offset = (page - 1) * per_page
        return {
            "count": queryset.count(),
            "page": page,
            "per_page": per_page,
            "items": queryset[offset : offset + per_page]
        }