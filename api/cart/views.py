import json

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from cart.models import CartItem
from cart.serializers import (
    CartAddSerializer,
    CartUpdateSerializer,
    ClearCartSerializer,
    LegacyImportSerializer,
)
from cart.services import add_product, cart_payload, export_csv, import_legacy, serialize_item
from core.exceptions import error_response
from research.models import Conversation


class CartView(APIView):
    @extend_schema(tags=["cart"], summary="The research cart with per-currency subtotals")
    def get(self, request: Request) -> Response:
        return Response(cart_payload())

    @extend_schema(request=CartAddSerializer, tags=["cart"], summary="Add a product to the cart")
    def post(self, request: Request) -> Response:
        serializer = CartAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        conversation_id = data.get("conversation_id")
        if conversation_id and not Conversation.objects.filter(pk=conversation_id).exists():
            conversation_id = None
        result = add_product(
            data["product"], quantity=data["quantity"], increment=data["increment"],
            conversation_id=conversation_id,
        )
        return Response(
            {"item": serialize_item(result.item), "created": result.created, "duplicate": result.duplicate,
             "cart": cart_payload()},
            status=status.HTTP_201_CREATED if result.created else status.HTTP_200_OK,
        )

    @extend_schema(request=ClearCartSerializer, tags=["cart"], summary='Empty the cart (confirm="CLEAR")',
                   operation_id="api_cart_clear")
    def delete(self, request: Request) -> Response:
        ClearCartSerializer(data=request.data).is_valid(raise_exception=True)
        CartItem.objects.all().delete()
        return Response(cart_payload())


class CartItemView(APIView):
    @extend_schema(request=CartUpdateSerializer, tags=["cart"], summary="Change quantity or notes")
    def patch(self, request: Request, item_id: int) -> Response:
        item = get_object_or_404(CartItem, pk=item_id)
        serializer = CartUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fields = list(serializer.validated_data)
        if not fields:
            return error_response(status.HTTP_400_BAD_REQUEST, "Nothing to update.")
        for name in fields:
            setattr(item, name, serializer.validated_data[name])
        item.save(update_fields=[*fields, "updated_at"])
        return Response({"item": serialize_item(item), "cart": cart_payload()})

    @extend_schema(tags=["cart"], summary="Remove an item")
    def delete(self, request: Request, item_id: int) -> Response:
        get_object_or_404(CartItem, pk=item_id).delete()
        return Response(cart_payload())


class CartImportView(APIView):
    @extend_schema(request=LegacyImportSerializer, tags=["cart"],
                   summary="Import the cart saved by earlier browser-only versions")
    def post(self, request: Request) -> Response:
        serializer = LegacyImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        imported = import_legacy(serializer.validated_data["items"])
        return Response({"imported": imported, "cart": cart_payload()})


class CartExportView(APIView):
    @extend_schema(tags=["cart"], summary="Download the cart as CSV or JSON (?format=csv|json)")
    def get(self, request: Request) -> HttpResponse:
        export_format = request.query_params.get("format", "csv")
        stamp = timezone.now().strftime("%Y%m%d-%H%M")
        if export_format == "json":
            body = json.dumps({"exported_at": timezone.now().isoformat(), **cart_payload()}, indent=2)
            response = HttpResponse(body, content_type="application/json")
            response["Content-Disposition"] = f'attachment; filename="marketmesh-cart-{stamp}.json"'
            return response
        if export_format != "csv":
            return error_response(status.HTTP_400_BAD_REQUEST, "format must be csv or json.")
        response = HttpResponse(export_csv(list(CartItem.objects.all())), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="marketmesh-cart-{stamp}.csv"'
        return response
