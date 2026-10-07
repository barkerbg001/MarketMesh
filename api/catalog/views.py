import time

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.products import from_scraped
from catalog.serializers import ProductSearchRequestSerializer, ProductSearchResponseSerializer
from catalog.services import search_products
from core.exceptions import error_response
from core.serializers import ErrorDetailSerializer
from history.models import SearchRun
from history.services import record_run
from retailers.registry import RETAILER_SLUGS


class ProductSearchView(APIView):
    @extend_schema(
        request=ProductSearchRequestSerializer,
        responses={
            200: ProductSearchResponseSerializer,
            400: ErrorDetailSerializer,
            422: ErrorDetailSerializer,
            502: ErrorDetailSerializer,
        },
        tags=["products"],
        summary="Search several retailers concurrently and merge the results",
    )
    def post(self, request: Request) -> Response:
        serializer = ProductSearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        retailers = list(dict.fromkeys(data["retailers"])) or list(RETAILER_SLUGS)
        query: str = data["query"].strip()
        if not query:
            return error_response(status.HTTP_400_BAD_REQUEST, "Search query must not be empty")

        started = time.perf_counter()
        outcome = search_products(query, retailers, data["max_results"])
        duration_ms = int((time.perf_counter() - started) * 1000)

        failed = not outcome.products and bool(outcome.errors)
        http_status = status.HTTP_502_BAD_GATEWAY if failed else status.HTTP_200_OK
        record_run(
            kind=SearchRun.Kind.PRODUCT_SEARCH,
            query=query,
            retailers=retailers,
            http_status=http_status,
            duration_ms=duration_ms,
            products=outcome.products,
            errors=outcome.errors,
        )

        if failed:
            return error_response(
                http_status,
                {"message": "No products found", "errors": outcome.errors},
            )

        retrieved_at = timezone.now()
        products = [
            {**product.to_dict(), **from_scraped(product, retrieved_at)} for product in outcome.products
        ]
        return Response(
            ProductSearchResponseSerializer(
                {
                    "query": outcome.query,
                    "retrieved_at": retrieved_at.isoformat(),
                    "products": products,
                    "errors": outcome.errors,
                }
            ).data
        )
