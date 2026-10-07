from rest_framework import serializers


class ConversationCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False, allow_blank=False)


class ConversationUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, min_length=1)


class SendMessageSerializer(serializers.Serializer):
    content = serializers.CharField(min_length=1, max_length=4000)
    cart_item_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, default=list, max_length=12
    )

    def validate_content(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Message must not be empty.")
        return value.strip()


class DeleteAllSerializer(serializers.Serializer):
    confirm = serializers.CharField()

    def validate_confirm(self, value: str) -> str:
        if value != "DELETE":
            raise serializers.ValidationError('Send {"confirm": "DELETE"} to delete all conversations.')
        return value
