from rest_framework import serializers
from .models import EventSignUp
from .ocr import rut_unformatted, rut_validation

class EventSignUpListSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventSignUp
        fields = '__all__'

    def validate_document(self, value):
        rut = rut_unformatted(value)
        if not rut_validation(value):
            raise serializers.ValidationError("RUT Inválido")
        return rut

class EventSignUpScanSerializer(serializers.Serializer):
    document_front_picture = serializers.ImageField()
    document_back_picture = serializers.ImageField()

class EventSignUpScanResutSerializer(serializers.Serializer):
    document = serializers.CharField(allow_null=True)
    first_names = serializers.CharField(allow_null=True)
    last_names = serializers.CharField(allow_null=True)
    sex = serializers.BooleanField(allow_null=True)
    born_date = serializers.DateField(allow_null=True)
    born_location = serializers.CharField(allow_null=True)
    document_number = serializers.IntegerField(allow_null=True)
    missing_data = serializers.ListField(child=serializers.CharField())
