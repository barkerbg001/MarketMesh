from rest_framework import serializers

from retailers.registry import RETAILER_CHOICES, RETAILER_SLUGS


class ProductSerializer(serializers.Serializer):
    key = serializers.CharField()
    title = serializers.CharField()
    url = serializers.CharField()
    seller = serializers.CharField(allow_null=True)
    source = serializers.CharField()
    source_type = serializers.ChoiceField(choices=["retailer", "web", "cart"])
    image_url = serializers.CharField(allow_null=True)
    price = serializers.CharField(allow_null=True)
    price_amount = serializers.CharField(allow_null=True)
    currency = serializers.CharField(allow_null=True)
    specs = serializers.DictField(child=serializers.CharField())
    retrieved_at = serializers.CharField(allow_null=True)


class SearchProductSerializer(ProductSerializer):
    """Normalized product plus the original scraper fields kept for compatibility."""

    retailer = serializers.CharField()
    rating = serializers.CharField(allow_null=True)
    in_stock = serializers.BooleanField(allow_null=True)


class ProductSearchRequestSerializer(serializers.Serializer):
    query = serializers.CharField(min_length=1, max_length=200, trim_whitespace=False)
    retailers = serializers.ListField(
        child=serializers.ChoiceField(choices=RETAILER_CHOICES),
        required=False,
        default=list(RETAILER_SLUGS),
        help_text="Retailers to search. Omitted or empty means all retailers.",
    )
    max_results = serializers.IntegerField(min_value=1, max_value=24, default=12)


class ProductSearchResponseSerializer(serializers.Serializer):
    query = serializers.CharField()
    retrieved_at = serializers.CharField()
    products = SearchProductSerializer(many=True)
    errors = serializers.DictField(child=serializers.CharField())
