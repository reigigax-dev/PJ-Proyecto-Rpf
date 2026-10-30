import pytesseract
<<<<<<< HEAD
from drf_spectacular.utils import extend_schema
=======
from django.utils import timezone
from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
>>>>>>> d3e81cb (Funcion principal de ecaneo y exportacion de registros a excel realizada)
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from .export import build_workbook
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
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            data = scan_carnet(
                serializer.validated_data['document_front_picture'],
                serializer.validated_data['document_back_picture'],
            )
        except pytesseract.TesseractNotFoundError:
            return Response(
                {'detail': 'Tesseract OCR no está instalado o TESSERACT_CMD apunta a una ruta incorrecta.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE, 
            )
        return Response(data, status=status.HTTP_200_OK)

XLSX_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

class EventSignUpExportAPIView(APIView):
    @extend_schema(
        responses = {(200, XLSX_TYPE): OpenApiResponse(OpenApiTypes.BINARY, description='Archivo Excel con todos los registros')},
    )
    def get(self, request):
        records = EventSignUp.objects.all().order_by('id')
        content = build_workbook(records, image_url=lambda f: request.build_absolute_uri(f.url))
        filename = f"registros_{timezone.localtime():%Y-%m-%d_%H%M}.xlsx"
        response = HttpResponse(content, content_type=XLSX_TYPE)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response