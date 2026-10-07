from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.serializers import HealthSerializer, MessageSerializer


class RootView(APIView):
    @extend_schema(responses=MessageSerializer, tags=["meta"])
    def get(self, request: Request) -> Response:
        return Response({"message": "MarketMesh API"})


class HealthView(APIView):
    @extend_schema(responses=HealthSerializer, tags=["health"])
    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})
