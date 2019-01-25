from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status


class UsersTest(TestCase):
    """
        Unit test file for testing Users app
    """

    def setUp(self):
        self.client = Client(HTTP_DEVICE='web', HTTP_VERSION='1.0')

    def test_professions(self):
        response = self.client.get(reverse('profession'), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
