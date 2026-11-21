from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, identify_hasher
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.forms import LoginForm, RegisterForm
from accounts.models import Address, Review
from accounts.tokens import account_activation_token
from store.models import Product

User = get_user_model()


class PasswordHashingTests(TestCase):
    def test_password_is_never_stored_in_plain_text(self):
        user = User.objects.create_user("a@test.com", "Parola123")
        self.assertNotEqual(user.password, "Parola123")
        self.assertNotIn("Parola123", user.password)

    def test_hash_uses_pbkdf2_sha256_with_expected_format(self):
        user = User.objects.create_user("a@test.com", "Parola123")
        algorithm, iterations, salt, digest = user.password.split("$")
        self.assertEqual(algorithm, "pbkdf2_sha256")
        self.assertGreaterEqual(int(iterations), 1_000_000)
        self.assertEqual(len(salt), 22)
        self.assertTrue(digest)

    def test_same_password_gives_different_hashes_because_of_salt(self):
        u1 = User.objects.create_user("a@test.com", "Parola123")
        u2 = User.objects.create_user("b@test.com", "Parola123")
        self.assertNotEqual(u1.password, u2.password)
        self.assertEqual(identify_hasher(u1.password).algorithm, "pbkdf2_sha256")

    def test_check_password_accepts_correct_and_rejects_wrong(self):
        user = User.objects.create_user("a@test.com", "Parola123")
        self.assertTrue(user.check_password("Parola123"))
        self.assertFalse(user.check_password("parola123"))
        self.assertTrue(check_password("Parola123", user.password))

    def test_unusable_password_when_none_given(self):
        user = User.objects.create_user("a@test.com")
        self.assertFalse(user.has_usable_password())


class UserModelTests(TestCase):
    def test_email_is_required(self):
        with self.assertRaises(ValueError):
            User.objects.create_user("", "Parola123")

    def test_email_domain_is_normalised(self):
        user = User.objects.create_user("Test@EXAMPLE.com", "Parola123")
        self.assertEqual(user.email, "Test@example.com")

    def test_names_are_capitalised_on_save(self):
        user = User.objects.create_user("a@test.com", "Parola123", first_name="iVAN", last_name="petrov")
        self.assertEqual((user.first_name, user.last_name), ("Ivan", "Petrov"))

    def test_name_validator_rejects_digits_and_lowercase_start(self):
        user = User(email="a@test.com", first_name="ivan1")
        with self.assertRaises(ValidationError):
            user.full_clean(exclude=["password"])

    def test_cyrillic_names_are_accepted(self):
        user = User(email="a@test.com", first_name="Иван", last_name="Петров")
        user.full_clean(exclude=["password"])

    def test_superuser_flags(self):
        admin = User.objects.create_superuser("root@test.com", "Parola123")
        self.assertTrue(admin.is_staff and admin.is_superuser and admin.is_active)

    def test_superuser_must_be_staff(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser("root@test.com", "Parola123", is_staff=False)


class ActivationTokenTests(TestCase):
    def test_token_is_valid_for_inactive_user(self):
        user = User.objects.create_user("a@test.com", "Parola123", is_active=False)
        token = account_activation_token.make_token(user)
        self.assertTrue(account_activation_token.check_token(user, token))

    def test_token_becomes_invalid_after_activation(self):
        user = User.objects.create_user("a@test.com", "Parola123", is_active=False)
        token = account_activation_token.make_token(user)
        user.is_active = True
        user.save()
        self.assertFalse(account_activation_token.check_token(user, token))

    def test_tampered_token_is_rejected(self):
        user = User.objects.create_user("a@test.com", "Parola123", is_active=False)
        token = account_activation_token.make_token(user)
        self.assertFalse(account_activation_token.check_token(user, token[:-1] + "x"))

    def test_token_of_one_user_is_invalid_for_another(self):
        u1 = User.objects.create_user("a@test.com", "Parola123", is_active=False)
        u2 = User.objects.create_user("b@test.com", "Parola123", is_active=False)
        self.assertFalse(account_activation_token.check_token(u2, account_activation_token.make_token(u1)))


class RegisterFormTests(TestCase):
    def data(self, **kw):
        base = {"email": "new@test.com", "password": "Parola123", "confirm_password": "Parola123"}
        base.update(kw)
        return base

    def test_valid_registration_hashes_password(self):
        form = RegisterForm(self.data())
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertTrue(user.password.startswith("pbkdf2_sha256$"))

    def test_passwords_must_match(self):
        self.assertIn("confirm_password", RegisterForm(self.data(confirm_password="Parola124")).errors)

    def test_password_requires_uppercase_lowercase_and_digit(self):
        for weak in ("parola123", "PAROLA123", "ParolaParola"):
            form = RegisterForm(self.data(password=weak, confirm_password=weak))
            self.assertIn("password", form.errors, weak)

    def test_password_shorter_than_eight_is_rejected(self):
        self.assertFalse(RegisterForm(self.data(password="Pa1", confirm_password="Pa1")).is_valid())

    def test_duplicate_active_email_is_rejected_case_insensitively(self):
        User.objects.create_user("new@test.com", "Parola123")
        self.assertIn("email", RegisterForm(self.data(email="NEW@test.com")).errors)

    def test_pending_activation_email_is_reported(self):
        User.objects.create_user("new@test.com", "Parola123", is_active=False)
        self.assertIn("awaiting activation", str(RegisterForm(self.data()).errors["email"]))


class LoginFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("a@test.com", "Parola123")

    def test_valid_credentials(self):
        form = LoginForm({"email": "A@test.com", "password": "Parola123"})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["user"], self.user)

    def test_wrong_password_gives_generic_message(self):
        form = LoginForm({"email": "a@test.com", "password": "Wrong123"})
        self.assertFalse(form.is_valid())
        self.assertIn("Invalid email or password.", form.non_field_errors())

    def test_unknown_email_gives_the_same_generic_message(self):
        form = LoginForm({"email": "nobody@test.com", "password": "Parola123"})
        self.assertIn("Invalid email or password.", form.non_field_errors())

    def test_inactive_account_is_flagged_only_with_correct_password(self):
        User.objects.create_user("b@test.com", "Parola123", is_active=False)
        ok = LoginForm({"email": "b@test.com", "password": "Parola123"})
        self.assertFalse(ok.is_valid())
        self.assertEqual(ok.errors.as_data()["__all__"][0].code, "account_inactive")
        bad = LoginForm({"email": "b@test.com", "password": "Wrong123"})
        self.assertNotEqual(bad.errors.as_data()["__all__"][0].code, "account_inactive")


class AddressTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("a@test.com", "Parola123")

    def make(self, **kw):
        data = dict(user=self.user, address_line="ul. Ivan Mihaylov 66", city="Blagoevgrad", postal_code="2700", country="Bulgaria")
        data.update(kw)
        return Address.objects.create(**data)

    def test_first_address_becomes_default(self):
        self.assertTrue(self.make().is_default)

    def test_only_one_default_address(self):
        first = self.make()
        second = self.make(is_default=True)
        first.refresh_from_db()
        self.assertFalse(first.is_default)
        self.assertTrue(second.is_default)

    def test_maximum_five_addresses(self):
        for _ in range(5):
            self.make()
        with self.assertRaises(ValueError):
            self.make()


class ReviewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("a@test.com", "Parola123", first_name="Ivan", last_name="Petrov")
        self.product = Product.objects.create(name="Tee", slug="tee", price="30.00")

    def test_one_review_per_user_per_product(self):
        Review.objects.create(product=self.product, user=self.user, rating=5, comment="ok")
        with self.assertRaises(Exception):
            Review.objects.create(product=self.product, user=self.user, rating=4, comment="again")

    def test_rating_must_be_between_one_and_five(self):
        for bad in (0, 6):
            review = Review(product=self.product, user=self.user, rating=bad, comment="x")
            with self.assertRaises(ValidationError):
                review.full_clean()

    def test_display_name_and_anonymous_fallback(self):
        self.assertEqual(Review(user=self.user).display_name, "Ivan Petrov")
        anon = User.objects.create_user("b@test.com", "Parola123")
        self.assertEqual(Review(user=anon).display_name, "Anonymous")

    def test_average_rating(self):
        other = User.objects.create_user("b@test.com", "Parola123")
        Review.objects.create(product=self.product, user=self.user, rating=5, comment="a")
        Review.objects.create(product=self.product, user=other, rating=3, comment="b")
        self.assertEqual(self.product.average_rating(), 4)
        self.assertEqual(self.product.review_count(), 2)
