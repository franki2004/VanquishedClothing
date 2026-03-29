from celery import shared_task
from django.utils import timezone
from .models import ProductVariantReservation

@shared_task
def release_expired_reservations():
    now = timezone.now()
    ProductVariantReservation.objects.filter(reserved_until__lte=now).delete()