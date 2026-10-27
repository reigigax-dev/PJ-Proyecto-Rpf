from rest_framework import serializers
from .models import EventSignUp

class EventSignUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventSignUp
        fields = '__all__'