"""
Test for the ingredient api

"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Ingredient,
    Recipe,
)

from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse('recipe:ingredient-list')


def create_user(email='user@example.com', password='testpass123'):
    """Create a user to test the ingredients api. """
    return get_user_model().objects.create_user(
        email=email,
        password=password,
    )


def detail_url(ingredient_id):
    """Return the detail url of the ingredient. """
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


class PublicIngredientsApiTests(TestCase):
    """ Test unauthenticated API requests. """

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """ Test authentication required to view ingredients"""
        res = self.client.get(INGREDIENTS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):
    """Test authenticated API requests. """

    def setUp(self):
        self.client = APIClient()
        self.user = create_user()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        """ Test retrieving a list of ingredients. """
        Ingredient.objects.create(user=self.user, name='Sugar')
        Ingredient.objects.create(user=self.user, name='Salt')

        res = self.client.get(INGREDIENTS_URL)
        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """Test the ingredient is only limited to the authenticated user . """
        other_user = create_user(
            email='test@example.com', password="testpass321")
        Ingredient.objects.create(user=other_user, name='vanilla')
        ingredient = Ingredient.objects.create(
            user=self.user, name='chocolate')

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertEqual(ingredients.count(), 1)
        self.assertIn(ingredient, ingredients)

    def test_update_ingredients(self):
        """ Test updating an ingredient. """
        ingredient = Ingredient.objects.create(user=self.user, name='Cheese')

        payload = {
            'name': 'Cream'
        }
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(payload['name'], ingredient.name)
        self.assertEqual(ingredient.user, self.user)

    def test_delete_ingredients(self):
        """Test deleting the ingredient successfully. """
        ingredient = Ingredient.objects.create(user=self.user, name='Chilli')

        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ingredient.objects.filter(id=ingredient.id).exists())

    # ______________filtering___________#

    def test_filter_ingredients_assigned_to_recipes(self):
        """ Test listing ingredients by those assigned to recieps. """
        ing1 = Ingredient.objects.create(user=self.user, name='Noodles')
        ing2 = Ingredient.objects.create(user=self.user, name='Cauliflower')

        r1 = Recipe.objects.create(user=self.user,
                                   title='Thai Ramein',
                                   price=Decimal('5.99'),
                                   time_minutes=34)
        r1.ingredients.add(ing1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        s1 = IngredientSerializer(ing1)
        s2 = IngredientSerializer(ing2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filter_ingredients_uniques(self):
        """ Test filtering the ingredients gives unique ingredients only. """

        ing1 = Ingredient.objects.create(user=self.user, name='Cooked Apple')
        Ingredient.objects.create(user=self.user, name='Chicken')

        r1 = Recipe.objects.create(user=self.user,
                                   title='Pancakes',
                                   time_minutes=25,
                                   price=Decimal('4.78'))
        r2 = Recipe.objects.create(user=self.user,
                                   title='French Tost',
                                   price=Decimal('20.99'),
                                   time_minutes=20)
        r1.ingredients.add(ing1)
        r2.ingredients.add(ing1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
