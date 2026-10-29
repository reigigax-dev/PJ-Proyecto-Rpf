import pytesseract
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from .ocr import scan_carnet
from .models import EventSignUp
from .serializers import (
    EventSignUpListSerializer,
    EventSignUpScanSerializer,
    EventSignUpScanResutSerializer,
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

class EventSignUpScanAPIView(generics.GenericAPIView):
    serializer_class = EventSignUpScanSerializer
    parser_classes = [MultiPartParser, FormParser]
    # permission_classes = [IsAuthenticated]

    @extend_schema(
        request={'multipart/form-data': EventSignUpScanSerializer},
        responses=EventSignUpScanResutSerializer,
        parameters=[
            OpenApiParameter(
                'debug', OpenApiTypes.BOOL, OpenApiParameter.QUERY,
                description='Si es true, incluye el texto leído por el OCR (para diagnosticar).',
            )
        ]
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        debug = request.query_params.get('debug', '').lower() in ('1', 'true', 'si')
        try:
            data = scan_carnet(
                serializer.validated_data['document_front_picture'],
                serializer.validated_data['document_back_picture'],
                debug=debug,
            )
        except pytesseract.TesseractNotFoundError:
            return Response(
                {'detail': 'Tesseract OCR no está instalado o TESSERACT_CMD apunta a una ruta incorrecta.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE, 
            )
        return Response(data, status=status.HTTP_200_OK)
