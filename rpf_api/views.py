from rest_framework import generics
from .models import EventSignUp
from .serializers import (
    EventSignUpListSerializer, 
)

class EventSignUpListAPIView(generics.ListAPIView):
    queryset = EventSignUp.objects.all()
    serializer_class = EventSignUpListSerializer
    pagination_class = None
    # permission_classes = [IsAuthenticated]
    # filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter, InStockFilterBackend,]
    # filterset_class = EventSignUpListFilter
    # search_fields = ['',]
    # ordering_fields = ['',]

class EventSignUpCreateAPIView(generics.CreateAPIView):
    serializer_class = EventSignUpListSerializer
    pagination_class = None
    # permission_classes = [IsAuthenticated]
    # filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter, InStockFilterBackend,]
    # filterset_class = EventSignUpListFilter
    # search_fields = ['',]
    # ordering_fields = ['',]

class EventSignUpUpdateAPIView(generics.RetrieveUpdateAPIView):
    queryset = EventSignUp.objects.all()
    serializer_class = EventSignUpListSerializer
    lookup_url_kwarg = 'signup_id'
    pagination_class = None
    # permission_classes = [IsAuthenticated]
    # filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter, InStockFilterBackend,]
    # filterset_class = EventSignUpListFilter
    # search_fields = ['',]
    # ordering_fields = ['',]

class EventSignUpDeleteAPIView(generics.RetrieveDestroyAPIView):
    queryset = EventSignUp.objects.all()
    serializer_class = EventSignUpListSerializer
    lookup_url_kwarg = 'signup_id'
    pagination_class = None
    # permission_classes = [IsAuthenticated]
    # filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter, InStockFilterBackend,]
    # filterset_class = EventSignUpListFilter
    # search_fields = ['',]
    # ordering_fields = ['',]
