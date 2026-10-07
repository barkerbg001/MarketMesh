from rest_framework import serializers


class ErrorDetailSerializer(serializers.Serializer):
    detail = serializers.JSONField()


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField()


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
