from django.test import TestCase
from django.contrib.auth.models import User


class TestAuthentication(TestCase):
    def setUp(self):
        self.test_user = User.objects.create_user('john.smith', 'john@smith.com', 'hunter2')

    def test_that_login_page_is_csrf_protected(self):
        response = self.client.get('/login/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'csrfmiddlewaretoken', response.content)

    def test_that_login_works(self):
        self.assertTrue(self.client.login(username='john.smith', password='hunter2'))
        response = self.client.get('/login/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[-1], ('/', 302))
