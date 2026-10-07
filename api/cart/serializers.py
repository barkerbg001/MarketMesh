from rest_framework import serializers

from cart.services import MAX_QUANTITY


def _http_url(value: str) -> str:
    if not value.lower().startswith(("http://", "https://")):
        raise serializers.ValidationError("Only http(s) links are allowed.")
    return value


class CartProductSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=500)
    url = serializers.URLField(max_length=2000, validators=[_http_url])
    seller = serializers.CharField(max_length=200, required=False, allow_blank=True, allow_null=True)
    source = serializers.CharField(max_length=200, required=False, allow_blank=True, allow_null=True)
    image_url = serializers.URLField(max_length=2000, required=False, allow_blank=True, allow_null=True,
                                     validators=[_http_url])
    price = serializers.CharField(max_length=64, required=False, allow_blank=True, allow_null=True)
    price_amount = serializers.CharField(max_length=32, required=False, allow_blank=True, allow_null=True)
    currency = serializers.CharField(max_length=3, required=False, allow_blank=True, allow_null=True)
    specs = serializers.DictField(child=serializers.CharField(max_length=300, allow_blank=True), required=False)
    retrieved_at = serializers.CharField(max_length=40, required=False, allow_blank=True, allow_null=True)


class CartAddSerializer(serializers.Serializer):
    product = CartProductSerializer()
    quantity = serializers.IntegerField(min_value=1, max_value=MAX_QUANTITY, default=1)
    increment = serializers.BooleanField(default=False)
    conversation_id = serializers.UUIDField(required=False, allow_null=True)


class CartUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, max_value=MAX_QUANTITY, required=False)
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class LegacyCartEntrySerializer(serializers.Serializer):
    title = serializers.CharField(max_length=500)
    url = serializers.URLField(max_length=2000, validators=[_http_url])
    retailer = serializers.CharField(max_length=50, required=False, allow_blank=True)
    price = serializers.CharField(max_length=64, required=False, allow_blank=True, allow_null=True)
    quantity = serializers.IntegerField(min_value=1, max_value=MAX_QUANTITY, default=1)


class LegacyImportSerializer(serializers.Serializer):
    items = LegacyCartEntrySerializer(many=True, max_length=200)


class ClearCartSerializer(serializers.Serializer):
    confirm = serializers.CharField()

    def validate_confirm(self, value: str) -> str:
        if value != "CLEAR":
            raise serializers.ValidationError('Send confirm="CLEAR" to empty the cart.')
        return value
