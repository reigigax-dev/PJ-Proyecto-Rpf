from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from rpf_api.models import EventSignUp

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bpm", ".gif"}

class Command(BaseCommand):
    help = "Elimina las imagenes almacenadas en 'media/' que no esten asociada a ningun registro"

    def add_arguments(self, parser):
        parser.add_argument("--borrar", action="store_true", help="Borra los archivos (sin esto solo los lista)")

    def handle(self, *args, **options):
        media = Path(settings.MEDIA_ROOT)
        if not media.exists():
            self.stdout.write("La carpeta 'media/' no existe")
            return

        in_use = set()
        for front, back in EventSignUp.objects.values_list("document_front_picture", "document_back_picture"):
            in_use.update(Path(name).as_posix() for name in (front, back) if name)

        orphans = [
            p for p in media.rglob("*")
            if p.is_file() and p.suffix.lower() in EXTENSIONS
            and p.relative_to(media).as_posix() not in in_use
        ]

        if not orphans:
            self.stdout.write(self.style.SUCCESS("No hay imágenes huérfanas"))

        for p in orphans:
            self.stdout.write(f"  {p.relative_to(media)}")
        if options["borrar"]:
            for p in orphans:
                p.unlink()
            self.stdout.write(self.style.SUCCESS(f"{len(orphans)} imágenes eliminadas."))
        else:
            self.stdout.write(self.style.WARNING(
                f"{len(orphans)} imágenes sin registro. Ejecuta nuebamente el comando con '--borrar' para eliminarlas"
            ))