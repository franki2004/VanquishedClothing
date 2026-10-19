from django.core.management.base import BaseCommand
from django.utils import timezone
from store.models import Product, ProductVariantReservation


class Command(BaseCommand):
    help = "Clear expired discounts and reservations"

    def handle(self, *args, **options):
        now = timezone.now()

        discounts = Product.objects.filter(
            discount_percent__gt=0,
            discount_end__lte=now,
        ).update(discount_percent=0, discount_start=None, discount_end=None)

        reservations, _ = ProductVariantReservation.objects.filter(
            reserved_until__lte=now
        ).delete()

        self.stdout.write(f"Cleared {discounts} discounts, {reservations} reservations")