from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from store.forms import DiscountForm
from store.models import Category, Product, ProductVariant, ProductVariantReservation, Tag


def make_product(name="Tee", price="50.00", **kw):
    return Product.objects.create(name=name, slug=name.lower().replace(" ", "-"), price=Decimal(price), **kw)


class PricingTests(TestCase):
    def test_sku_is_generated_from_primary_key(self):
        p = make_product()
        self.assertEqual(p.sku, f"P{p.pk:06d}")

    def test_price_without_discount(self):
        p = make_product()
        self.assertFalse(p.is_discount_active)
        self.assertEqual(p.final_price, Decimal("50.00"))
        self.assertEqual(p.discount_status, "none")

    def test_active_discount_open_ended(self):
        p = make_product(discount_percent=20)
        self.assertEqual(p.final_price, Decimal("40.00"))
        self.assertEqual(p.discount_status, "active")

    def test_active_discount_inside_window(self):
        now = timezone.now()
        p = make_product(discount_percent=30, discount_start=now - timedelta(days=1), discount_end=now + timedelta(days=1))
        self.assertTrue(p.is_discount_active)
        self.assertEqual(p.final_price, Decimal("35.00"))
        self.assertEqual(p.discount_status, "active")

    def test_scheduled_discount_is_not_applied_yet(self):
        now = timezone.now()
        p = make_product(discount_percent=30, discount_start=now + timedelta(days=1), discount_end=now + timedelta(days=5))
        self.assertFalse(p.is_discount_active)
        self.assertEqual(p.final_price, Decimal("50.00"))
        self.assertEqual(p.discount_status, "scheduled")

    def test_expired_discount_is_not_applied(self):
        now = timezone.now()
        p = make_product(discount_percent=30, discount_start=now - timedelta(days=5), discount_end=now - timedelta(days=1))
        self.assertFalse(p.is_discount_active)
        self.assertEqual(p.final_price, Decimal("50.00"))
        self.assertEqual(p.discount_status, "expired")

    def test_final_price_is_rounded_to_cents(self):
        p = make_product(price="19.99", discount_percent=15)
        self.assertEqual(p.final_price, Decimal("16.99"))


class StockAndReservationTests(TestCase):
    def setUp(self):
        self.variant = ProductVariant.objects.create(product=make_product(), size="M", stock=5)

    def reserve(self, qty, delta):
        return ProductVariantReservation.objects.create(
            variant=self.variant, session_key="s1", quantity=qty, reserved_until=timezone.now() + delta
        )

    def test_available_equals_stock_without_reservations(self):
        self.assertEqual(self.variant.available_quantity(), 5)

    def test_active_reservation_reduces_availability(self):
        self.reserve(2, timedelta(minutes=10))
        self.assertEqual(self.variant.available_quantity(), 3)

    def test_expired_reservation_is_ignored(self):
        self.reserve(2, timedelta(minutes=-1))
        self.assertEqual(self.variant.available_quantity(), 5)

    def test_reservations_of_several_customers_add_up(self):
        self.reserve(2, timedelta(minutes=10))
        self.reserve(3, timedelta(minutes=10))
        self.assertEqual(self.variant.available_quantity(), 0)

    def test_expire_method_releases_stock(self):
        r = self.reserve(4, timedelta(minutes=10))
        r.expire()
        self.assertEqual(self.variant.available_quantity(), 5)

    def test_size_order_is_set_and_variants_sorted(self):
        p = self.variant.product
        ProductVariant.objects.create(product=p, size="XS", stock=1)
        ProductVariant.objects.create(product=p, size="2XL", stock=1)
        self.assertEqual([v.size for v in p.variants.all()], ["XS", "M", "2XL"])

    def test_sold_out_detection(self):
        p = self.variant.product
        self.assertFalse(p.is_sold_out)
        self.variant.stock = 0
        self.variant.save()
        self.assertTrue(Product.objects.get(pk=p.pk).is_sold_out)


class TagTests(TestCase):
    def test_tag_names_are_stored_in_upper_case(self):
        self.assertEqual(Tag.objects.create(name="summer").name, "SUMMER")


class RelatedProductsTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Tees", slug="tees")
        self.other_cat = Category.objects.create(name="Pants", slug="pants")
        self.tag = Tag.objects.create(name="Cotton")
        self.main = make_product("Main", status="active", category=self.cat)
        self.main.tags.add(self.tag)

    def test_manual_relations_come_first(self):
        manual = make_product("Manual", status="active", category=self.other_cat)
        self.main.related_products.add(manual)
        same = make_product("Same", status="active", category=self.cat)
        self.assertEqual(self.main.get_related_products(), [manual, same])

    def test_category_match_outranks_a_single_shared_tag(self):
        by_cat = make_product("ByCat", status="active", category=self.cat)
        by_tag = make_product("ByTag", status="active", category=self.other_cat)
        by_tag.tags.add(self.tag)
        result = self.main.get_related_products()
        self.assertEqual(result[0], by_cat)
        self.assertIn(by_tag, result)

    def test_drafts_and_unrelated_products_are_excluded(self):
        make_product("Draft", status="draft", category=self.cat)
        make_product("Unrelated", status="active", category=self.other_cat)
        self.assertEqual(self.main.get_related_products(), [])

    def test_product_is_not_related_to_itself(self):
        self.assertNotIn(self.main, self.main.get_related_products())

    def test_limit_is_respected(self):
        for i in range(5):
            make_product(f"P{i}", status="active", category=self.cat)
        self.assertEqual(len(self.main.get_related_products(limit=3)), 3)


class DiscountFormTests(TestCase):
    def payload(self, **kw):
        now = timezone.now()
        data = {
            "discount_percent": 20,
            "discount_start": (now + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"),
            "discount_end": (now + timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
        }
        data.update(kw)
        return data

    def test_valid_form(self):
        self.assertTrue(DiscountForm(self.payload()).is_valid())

    def test_percent_bounds(self):
        for bad in (0, 91, -5):
            self.assertFalse(DiscountForm(self.payload(discount_percent=bad)).is_valid(), bad)

    def test_end_must_be_after_start(self):
        now = timezone.now()
        form = DiscountForm(self.payload(
            discount_start=(now + timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
            discount_end=(now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
        ))
        self.assertFalse(form.is_valid())

    def test_end_in_the_past_is_rejected(self):
        now = timezone.now()
        form = DiscountForm(self.payload(
            discount_start=(now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M"),
            discount_end=(now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
        ))
        self.assertFalse(form.is_valid())


class ExpireDiscountsCommandTests(TestCase):
    def test_expired_discounts_and_reservations_are_cleared(self):
        now = timezone.now()
        old = make_product("Old", discount_percent=40, discount_start=now - timedelta(days=3), discount_end=now - timedelta(days=1))
        live = make_product("Live", discount_percent=40, discount_start=now - timedelta(days=1), discount_end=now + timedelta(days=1))
        variant = ProductVariant.objects.create(product=live, size="S", stock=3)
        ProductVariantReservation.objects.create(variant=variant, session_key="x", quantity=1, reserved_until=now - timedelta(minutes=1))
        ProductVariantReservation.objects.create(variant=variant, session_key="y", quantity=1, reserved_until=now + timedelta(minutes=5))
        out = StringIO()
        call_command("expire_discounts", stdout=out)
        old.refresh_from_db(); live.refresh_from_db()
        self.assertEqual(old.discount_percent, 0)
        self.assertIsNone(old.discount_end)
        self.assertEqual(live.discount_percent, 40)
        self.assertEqual(ProductVariantReservation.objects.count(), 1)
        self.assertIn("Cleared 1 discounts, 1 reservations", out.getvalue())
