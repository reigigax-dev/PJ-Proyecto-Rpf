from rest_framework import serializers
from .models import EventSignUp

class EventSignUpListSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventSignUp
        fields = '__all__'