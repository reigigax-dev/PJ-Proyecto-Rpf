from django.shortcuts import render
from rest_framework import generics
from .serializers import EventSignUpSerializer
from .models import EventSignUp

class EventSignUpListAPIView(generics.ListAPIView):
    queryset = EventSignUp.objects.all()
    serializer_class = EventSignUpSerializer