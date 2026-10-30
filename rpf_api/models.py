from django.db import models


# TABLA REGISTROS DE EVENTO
#  REQUERIDOS:
#  - rut*                   (document)
#  - nombres*               (first_names)
#  - apellidos*             (last_names)
#  - sexo*                  (sex)
#  - fecha_nacimiento*      (born_date)
#
#  OPCIONALES:
#  - lugar_nacimiento       (born_location)
#  - n_documento            (document_number)
#  - foto_frontal_carnet    (document_front_picture)  
#  - foto_trasera_carnet    (document_back_picture)

class EventSignUp(models.Model):
    # Requeridos
    document = models.CharField(blank=False, null=False, max_length=9)
    first_names = models.CharField(blank=False, null=False, max_length=350)
    last_names = models.CharField(blank=False, null=False, max_length=350)
    sex = models.BooleanField(blank=False, null=False)
    born_date = models.DateField(blank=False, null=False)

    # Opcionales
    born_location = models.CharField(blank=True, null=True, max_length=250)
    document_number = models.PositiveIntegerField(blank=True, null=True)
    # Almacenados como blob
    document_front_picture = models.ImageField(blank=True, null=True)
    document_back_picture = models.ImageField(blank=True, null=True)