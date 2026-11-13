from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.bookings.tests import make_property, make_user
from apps.properties.models import PropertyImage
from apps.wishlist.models import Wishlist, WishlistItem

WISHLIST_URL = "/api/wishlist/"


class WishlistAPITests(APITestCase):
    def setUp(self):
        self.host = make_user("whost", User.Role.HOST)
        self.guest = make_user("wguest")
        self.other = make_user("wguest2")
        self.admin = make_user("wadmin", User.Role.ADMIN)
        self.prop = make_property(self.host)
        self.client = APIClient()

    def login(self, user):
        self.client.force_authenticate(user=user)

    def add(self, property_id):
        return self.client.post(WISHLIST_URL, {"property": property_id}, format="json")

    # ---------- permissions ----------
    def test_anonymous_gets_401(self):
        self.assertEqual(self.client.get(WISHLIST_URL).status_code, 401)
        self.assertEqual(self.add(self.prop.id).status_code, 401)

    def test_host_and_admin_get_403(self):
        for user in (self.host, self.admin):
            self.login(user)
            self.assertEqual(self.client.get(WISHLIST_URL).status_code, 403)
            self.assertEqual(self.add(self.prop.id).status_code, 403)

    def test_wishlist_auto_created_by_signal(self):
        self.assertTrue(Wishlist.objects.filter(user=self.guest).exists())

    # ---------- add ----------
    def test_add_creates_item(self):
        self.login(self.guest)
        resp = self.add(self.prop.id)
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertTrue(body["created"])
        self.assertEqual(body["item"]["property"]["id"], self.prop.id)
        self.assertEqual(WishlistItem.objects.count(), 1)

    def test_add_duplicate_is_idempotent(self):
        self.login(self.guest)
        first = self.add(self.prop.id).json()
        resp = self.add(self.prop.id)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertFalse(body["created"])
        self.assertEqual(body["item"]["id"], first["item"]["id"])
        self.assertEqual(WishlistItem.objects.count(), 1)

    def test_add_inactive_property_400(self):
        inactive = make_property(self.host, title="Hidden", is_active=False)
        self.login(self.guest)
        resp = self.add(inactive.id)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("property", resp.json()["errors"])
        self.assertEqual(WishlistItem.objects.count(), 0)

    def test_add_invalid_payloads_400(self):
        self.login(self.guest)
        for payload in ({}, {"property": 999999}, {"property": "abc"}, {"property": None}):
            with self.subTest(payload=payload):
                resp = self.client.post(WISHLIST_URL, payload, format="json")
                self.assertEqual(resp.status_code, 400)
                self.assertIn("property", resp.json()["errors"])

    # ---------- list ----------
    def test_list_shape_and_card_fields(self):
        self.login(self.guest)
        self.add(self.prop.id)
        body = self.client.get(WISHLIST_URL).json()
        for key in ("count", "next", "previous", "results"):
            self.assertIn(key, body)
        card = body["results"][0]["property"]
        for key in ("id", "title", "price_per_night", "average_rating", "review_count", "cover_image", "host"):
            self.assertIn(key, card)
        self.assertEqual(card["host"]["id"], self.host.id)
        self.assertIsNone(card["cover_image"])  # image upload nahi hui

    def test_cover_image_present_when_image_exists(self):
        PropertyImage.objects.create(property=self.prop, image="properties/x.jpg", is_primary=True)
        self.login(self.guest)
        self.add(self.prop.id)
        card = self.client.get(WISHLIST_URL).json()["results"][0]["property"]
        self.assertIsNotNone(card["cover_image"])

    def test_list_only_own_items(self):
        other_prop = make_property(self.host, title="Other")
        self.login(self.guest)
        self.add(self.prop.id)
        self.login(self.other)
        self.add(other_prop.id)

        self.login(self.guest)
        body = self.client.get(WISHLIST_URL).json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["property"]["id"], self.prop.id)

    def test_inactive_property_hidden_but_row_kept(self):
        self.login(self.guest)
        self.add(self.prop.id)
        self.prop.is_active = False
        self.prop.save()
        self.assertEqual(self.client.get(WISHLIST_URL).json()["count"], 0)
        self.assertEqual(WishlistItem.objects.count(), 1)
        self.prop.is_active = True
        self.prop.save()
        self.assertEqual(self.client.get(WISHLIST_URL).json()["count"], 1)

    def test_list_no_n_plus_one(self):
        self.login(self.guest)

        def add_props(n):
            for i in range(n):
                p = make_property(self.host, title=f"P{WishlistItem.objects.count()}-{i}")
                PropertyImage.objects.create(property=p, image="properties/a.jpg", is_primary=True)
                self.add(p.id)

        add_props(2)
        with CaptureQueriesContext(connection) as small:
            self.client.get(WISHLIST_URL)
        add_props(4)
        with CaptureQueriesContext(connection) as big:
            self.client.get(WISHLIST_URL)
        self.assertEqual(len(small.captured_queries), len(big.captured_queries))

    # ---------- delete ----------
    def test_delete_own_item(self):
        self.login(self.guest)
        item_id = self.add(self.prop.id).json()["item"]["id"]
        resp = self.client.delete(f"{WISHLIST_URL}{item_id}/")
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(WishlistItem.objects.count(), 0)

    def test_delete_other_users_item_404(self):
        self.login(self.other)
        item_id = self.add(self.prop.id).json()["item"]["id"]
        self.login(self.guest)
        self.assertEqual(self.client.delete(f"{WISHLIST_URL}{item_id}/").status_code, 404)
        self.assertEqual(WishlistItem.objects.count(), 1)

    def test_delete_unknown_item_404(self):
        self.login(self.guest)
        self.assertEqual(self.client.delete(f"{WISHLIST_URL}999999/").status_code, 404)

    def test_delete_by_property(self):
        self.login(self.other)
        self.add(self.prop.id)
        self.login(self.guest)
        self.add(self.prop.id)
        url = f"{WISHLIST_URL}property/{self.prop.id}/"
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.delete(url).status_code, 404)
        # doosre user ki item safe rehni chahiye
        self.assertEqual(WishlistItem.objects.filter(wishlist__user=self.other).count(), 1)

    # ---------- ids ----------
    def test_ids_endpoint(self):
        p2 = make_property(self.host, title="Second")
        self.login(self.guest)
        self.add(self.prop.id)
        self.add(p2.id)
        resp = self.client.get(WISHLIST_URL + "ids/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(sorted(resp.json()["property_ids"]), sorted([self.prop.id, p2.id]))