from drf_spectacular.openapi import AutoSchema as SpectacularAutoSchema
from drf_spectacular.types import OpenApiTypes


class AutoSchema(SpectacularAutoSchema):
    """Views without a declared response serializer are documented as a JSON object."""

    def get_response_serializers(self):
        if getattr(self.view, "serializer_class", None) or hasattr(self.view, "get_serializer"):
            return super().get_response_serializers()
        return OpenApiTypes.OBJECT
