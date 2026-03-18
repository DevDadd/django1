from rest_framework import serializers


class QuestionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    content = serializers.CharField()