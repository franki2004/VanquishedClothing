from django.db import migrations, models
from django.db.models import F


def backfill(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    OrderItem = apps.get_model("orders", "OrderItem")
    Order.objects.filter(status="completed", delivered_at__isnull=True).update(
        delivered_at=F("created_at")
    )
    OrderItem.objects.filter(return_requested=True, return_status="").update(
        return_status="requested"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0005_order_stripe_session_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="delivered_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="return_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("requested", "Return requested"),
                    ("approved", "Return approved"),
                    ("rejected", "Return declined"),
                ],
                default="",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="return_admin_comment",
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]