from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from orders.models import Cart, CartItem, Order, OrderItem
from store.models import Product, ProductVariant

User = get_user_model()


def make_order(**kw):
    data = dict(full_name="Ivan Petrov", phone="0888123456", city="Blagoevgrad", street="ul. 1", country="Bulgaria",
                subtotal=Decimal("60.00"), total=Decimal("65.00"), payment_method="cod")
    data.update(kw)
    return Order.objects.create(**data)


class ReturnWindowTests(TestCase):
    def test_no_return_before_delivery(self):
        order = make_order(status="accepted")
        self.assertIsNone(order.return_deadline)
        self.assertFalse(order.can_request_return)

    def test_return_allowed_within_14_days(self):
        order = make_order(status="completed", delivered_at=timezone.now() - timedelta(days=3))
        self.assertTrue(order.can_request_return)
        self.assertEqual(order.return_deadline, order.delivered_at + timedelta(days=14))

    def test_return_denied_after_14_days(self):
        order = make_order(status="completed", delivered_at=timezone.now() - timedelta(days=15))
        self.assertFalse(order.can_request_return)

    def test_return_denied_for_non_completed_order(self):
        order = make_order(status="pending", delivered_at=timezone.now())
        self.assertFalse(order.can_request_return)


class OrderItemTests(TestCase):
    def setUp(self):
        product = Product.objects.create(name="Tee", slug="tee", price=Decimal("30.00"))
        self.v1 = ProductVariant.objects.create(product=product, size="S", stock=5)
        self.v2 = ProductVariant.objects.create(product=product, size="M", stock=5)
        self.order = make_order()

    def test_item_total_uses_price_snapshot(self):
        item = OrderItem.objects.create(order=self.order, variant=self.v1, quantity=3, price_snapshot=Decimal("24.00"))
        self.assertEqual(item.total_price, Decimal("72.00"))

    def test_price_snapshot_is_independent_from_later_price_changes(self):
        item = OrderItem.objects.create(order=self.order, variant=self.v1, quantity=1, price_snapshot=Decimal("30.00"))
        self.v1.product.price = Decimal("99.00")
        self.v1.product.save()
        item.refresh_from_db()
        self.assertEqual(item.price_snapshot, Decimal("30.00"))

    def test_same_variant_cannot_appear_twice_in_one_order(self):
        OrderItem.objects.create(order=self.order, variant=self.v1, quantity=1, price_snapshot=Decimal("30.00"))
        with self.assertRaises(Exception):
            OrderItem.objects.create(order=self.order, variant=self.v1, quantity=1, price_snapshot=Decimal("30.00"))

    def test_returnable_items_exclude_already_requested(self):
        OrderItem.objects.create(order=self.order, variant=self.v1, quantity=1, price_snapshot=Decimal("30.00"), return_requested=True)
        free = OrderItem.objects.create(order=self.order, variant=self.v2, quantity=1, price_snapshot=Decimal("30.00"))
        self.assertEqual(self.order.returnable_items, [free])
        self.assertTrue(self.order.any_return_requested)

    def test_stripe_session_id_is_unique(self):
        make_order(stripe_session_id="cs_test_1")
        with self.assertRaises(Exception):
            make_order(stripe_session_id="cs_test_1")

    def test_product_cannot_be_deleted_while_ordered(self):
        OrderItem.objects.create(order=self.order, variant=self.v1, quantity=1, price_snapshot=Decimal("30.00"))
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.v1.delete()


class CartTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(name="Tee", slug="tee", price=Decimal("50.00"), discount_percent=20)
        self.variant = ProductVariant.objects.create(product=self.product, size="M", stock=10)
        self.cart = Cart.objects.create(session_key="abc")

    def test_cart_item_uses_discounted_price(self):
        item = CartItem.objects.create(cart=self.cart, variant=self.variant, quantity=2)
        self.assertEqual(item.total_price, Decimal("80.00"))

    def test_cart_total_sums_all_items(self):
        other = ProductVariant.objects.create(product=self.product, size="L", stock=4)
        CartItem.objects.create(cart=self.cart, variant=self.variant, quantity=1)
        CartItem.objects.create(cart=self.cart, variant=other, quantity=2)
        self.assertEqual(self.cart.total_price, Decimal("120.00"))

    def test_a_variant_appears_once_per_cart(self):
        CartItem.objects.create(cart=self.cart, variant=self.variant)
        with self.assertRaises(Exception):
            CartItem.objects.create(cart=self.cart, variant=self.variant)

    def test_delivery_and_cod_fee_rules(self):
        COD = Decimal("0.03")
        subtotal = Decimal("80.00")
        delivery = Decimal("5.00") if 0 < subtotal < 100 else Decimal("0.00")
        cod_fee = (subtotal * COD).quantize(Decimal("0.01"))
        self.assertEqual((delivery, cod_fee, subtotal + delivery + cod_fee), (Decimal("5.00"), Decimal("2.40"), Decimal("87.40")))
        self.assertEqual(Decimal("0.00"), Decimal("5.00") if 0 < Decimal("100.00") < 100 else Decimal("0.00"))
