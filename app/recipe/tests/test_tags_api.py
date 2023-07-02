"""
Test for the tags API

"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Tag,
    Recipe,
)

from recipe.serializers import (
    TagSerializer,
    RecipeSerializer,
)


TAGS_URL = reverse('recipe:tag-list')


def create_user(email='user@example.com', password='testpass123'):
    """Create and return a user. """
    return get_user_model().objects.create_user(email=email, password=password)


def detail_url(tag_id):
    """Return the url for the specific tag"""
    return reverse('recipe:tag-detail', args=[tag_id])


class PublicTagsApiTests(TestCase):
    """Test unauthenticated API requests. """

    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to retrieve tags. """
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTests(TestCase):
    """Test authenticated API requests """

    def setUp(self) -> None:
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """Test retrieving a list of tags"""
        Tag.objects.create(user=self.user, name='Vegan')
        Tag.objects.create(user=self.user, name='Desert')

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        """Test list of the tags is limited to authenticated user. """

        otheruser = create_user(email="user5@example.com")
        Tag.objects.create(user=otheruser, name='Fruity')
        tag = Tag.objects.create(user=self.user, name='Comfort Food')

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)

    def test_update_tag(self):
        """Test updating the tag by authenticate users. """

        tag = Tag.objects.create(user=self.user, name='Vegetrian')

        url = detail_url(tag_id=tag.id)
        payload = {
            'name': 'Non-Vegetrian'
        }
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])
        self.assertEqual(tag.user, self.user)

    def test_deleting_tag(self):
        """Test deleting the tag by authenticated respective user. """

        tag = Tag.objects.create(user=self.user, name='Dry')

        url = detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Tag.objects.filter(id=tag.id).exists())

    # _______________filtering_________________#

    def test_filter_tag_assigned_to_recipe(self):
        """ Test listing tags assigned to recipe. """
        tag1 = Tag.objects.create(user=self.user, name='Breakfast')
        tag2 = Tag.objects.create(user=self.user, name='Dinner')

        r1 = Recipe.objects.create(user=self.user,
                                   title='Eggs Benedict',
                                   price=Decimal('14.55'),
                                   time_minutes=20)
        r1.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filter_unique_tag(self):
        """ Test listing unique tag while filtering the recipe by tag. """
        tag1 = Tag.objects.create(user=self.user, name='Summer Drinks')
        Tag.objects.create(user=self.user, name='Bingo')

        r1 = Recipe.objects.create(user=self.user,
                                   title='Moccha',
                                   price=Decimal('10.11'),
                                   time_minutes=10)
        r2 = Recipe.objects.create(user=self.user,
                                   title='Magarita',
                                   price=Decimal('15.45'),
                                   time_minutes=15)
        r1.tags.add(tag1)
        r2.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
