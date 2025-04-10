from ninja.pagination import PaginationBase
from ninja.schema import Schema
from typing import Any

# pagination.py
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

         # Converta o queryset para lista se necessário
        if not isinstance(queryset, list):
            queryset = list(queryset)
        
        items = queryset[offset:offset + per_page]

        return {
            "count": len(queryset) if isinstance(queryset, list) else queryset.count(),
            "page": page,
            "per_page": per_page,
            "items": items,
        }