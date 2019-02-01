from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status
from config.models import Config
from .models import StargramzUser, ProfileImage, SettingsNotifications, VanityUrl, GroupType
from .constants import OLD_PASSWORD_ERROR_CODE, NEW_OLD_SAME_ERROR_CODE
import json
import uuid


class UsersTest(TestCase):
    """
        Unit test file for testing Users app
    """

    fixtures = ['relations.json',
                'occasions.json',
                'orderrelations.json',
                'profession.json',
                'roles.json',
                'config.json'
                ]

    def setUp(self):

        self.header = {"HTTP_DEVICE": "web", "HTTP_VERSION": '1.0'}
        self.client = Client(**self.header)
        self.register_params = {
            "first_name": "aswin",
            "last_name": "mohan",
            "password": "qburst@123",
            "email": "aswinmohan@qburst.com",
            "role": "R1001"
        }

        self.corrupted_register_params = {
            "first_name": "",
            "last_name": "",
            "password": "",
            "email": "",
            "role": ""
        }
        self.login_params = {
            "username": "aswinmohan@qburst.com",
            "password": "qburst@123"
        }

        self.social_signup_params = {
            "username": "aswinmohan@qburst.com",
            "first_name": "Aswin",
            "last_name": "Mohan",
            "sign_up_source": "2",
            "date_of_birth": "1995-05-01",
            "profile_photo": "profile_photo",
            "nick_name": "Tank",
            "fb_id": "facebook/5456698/testing/id",
            "gp_id": "google/5sdfdsdf/testing/id",
            "in_id": "instagram/sdfsdfsdf/testing/id",
            "tw_id": "twitter/jhgkjhg/testing/id",
            "role": "R1002"
        }

        self.celebrity_profile_data = {
            "rate": "45",
            "weekly_limits": 10,
            "profession": ["2", "12"],
            "profile_video": "home/key/key.jpg",
            "availability": 'true',
            'description': "gfdgd",
            'charity': "dfg"
        }
        self.notification_settings_params = {
            "celebrity_starsona_request": 'true',
            "celebrity_starsona_message": 'false',
            "celebrity_account_updates": 'true',
            "fan_account_updates": 'false',
            "fan_starsona_messages": 'false',
            "fan_starsona_videos": 'true',
            "fan_email_starsona_videos": 'true',
            "secondary_email": "aswinmohan+secondary@qburst.com",
            "email_notification": 'true',
            "mobile_country_code": "49",
            "mobile_number": "9874563210",
            "mobile_notification": 'true'
        }
        self.group_account_params = {
            "contact_first_name": "Aswin",
            "contact_last_name": 'Mohan',
            "description": "Who are you?",
            "tags": " #search",
            "website": "https://www.google.com",
            "phone": "968-5895-888",
            "address": 'dddd',
            "address_2": 'dd',
            "city": 'd',
            "state": 'dd',
            "zip": '1321',
            "group_type": 2000
        }

    # utility functions

    def register_user_with_data(self, role='fan'):
        """
        This is a utility function which will register a user as fan, celebrity or group for easy client object
        :param role:
        :return:
        """

        register_params = self.register_params.copy()
        if role is 'celebrity':
            register_params.update({'role': "R1002"})
        elif role is 'group':
            register_params.update({'role': "R1004", 'email': "aswinmohan+group@qburst.com"})
        elif role is 'fan':
            register_params.update({'email': "aswinmohan+fan@qburst.com"})
        response = self.client.post(
            reverse('register'), content_type='application/json', data=json.dumps(register_params)
        )
        data = json.loads(response.content)
        token = data.get("data").get("user").get('authentication_token')
        header = self.header.copy()
        header.update({"HTTP_AUTHORIZATION": 'token '+token})
        client = Client(**header)
        return client

    # Register API tests

    def test_register(self):
        """
        Simple register API test
        :return:
        """

        response = self.client.post(
            reverse('register'), content_type='application/json', data=json.dumps(self.register_params)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_register_existing_email(self):
        """
        Simple register API test with existing email address
        :return:
        """

        self.client.post(
            reverse('register'), content_type='application/json', data=json.dumps(self.register_params)
        )

        response = self.client.post(
            reverse('register'), content_type='application/json', data=json.dumps(self.register_params)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_empty_parameter(self):
        """
        Simple register API test with empty email address and other empty data
        :return:
        """

        response = self.client.post(
            reverse('register'), content_type='application/json', data=json.dumps(self.corrupted_register_params)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_email(self):
        """
        Simple register API test with invalid email address
        :return:
        """

        register_params = self.register_params.copy()
        register_params.update({"email": "kjhdgkjhfghkjghjk"})
        response = self.client.post(
            reverse('register'), content_type='application/json', data=json.dumps(register_params)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_validation(self):
        """
        Simple register API test for checking password validations
        :return:
        """

        numeric_password_register_params = self.register_params.copy()
        small_password_register_params = self.register_params.copy()
        without_symbol_password_register_params = self.register_params.copy()

        numeric_password_register_params.update({"password": "123456789"})
        small_password_register_params.update({"password": "a@1"})
        without_symbol_password_register_params.update({"password": "aswinmohan123"})

        response = self.client.post(
            reverse('register'), content_type='application/json', data=json.dumps(numeric_password_register_params)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(
            reverse('register'), content_type='application/json', data=json.dumps(small_password_register_params)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(
            reverse('register'), content_type='application/json',
            data=json.dumps(without_symbol_password_register_params)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_referral_code(self):
        """
        Simple register API test with incorrect referral code and correct referral code, also the testing of campaign
        :return:
        """

        register_params = self.register_params.copy()
        register_params.update({"referral_code": "fghfhgfghf"})
        response = self.client.post(
            reverse('register'), content_type='application/json', data=json.dumps(self.register_params)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # Login API tests

    def test_login(self):
        """
        Simple login
        :return:
        """

        self.client.post(
            reverse('register'), content_type='application/json', data=json.dumps(self.register_params)
        )
        response = self.client.post(
            reverse('login'), content_type='application/json', data=json.dumps(self.login_params)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_incorrect_email_or_password(self):
        """
        Login of a fan with incorrect Email and incorrect password
        :return:
        """

        email_unknown_login_params = self.login_params.copy()
        password_unknown_login_params = self.login_params.copy()

        self.client.post(
            reverse('register'), content_type='application/json', data=json.dumps(self.register_params)
        )
        email_unknown_login_params.update({"username": "aswinmohan+unknown@qburst.com"})
        password_unknown_login_params.update({"password": "abcdef@123"})

        response = self.client.post(
            reverse('login'), content_type='application/json', data=json.dumps(email_unknown_login_params)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(
            reverse('login'), content_type='application/json', data=json.dumps(password_unknown_login_params)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_celebrity(self):
        """
        Register a user as a celebrity and trying to login
        :return:
        """

        register_params = self.register_params.copy()
        register_params.update({"role": "R1002"})
        self.client.post(
            reverse('register'), content_type='application/json', data=json.dumps(register_params)
        )
        response = self.client.post(
            reverse('login'), content_type='application/json', data=json.dumps(self.login_params)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authentication_token(self):
        """
        Test the authentication token which returns when a user register
        :return:
        """

        response = self.client.post(
            reverse('register'), content_type='application/json', data=json.dumps(self.register_params)
        )
        data = json.loads(response.content)
        token = data.get("data").get("user").get('authentication_token')
        self.assertIsNotNone(token)

    # email validate API tests

    def test_email_validate(self):
        """
        The function will validate different emails
        :return:
        """

        normal_email = {"email": "aswinmohan+1@qburst.com"}
        invalid_email = {"email": "hjfakjhafgkhjd"}
        registered_email = {"email": "aswinmohan+fan@qburst.com"}

        response = self.client.post(
            reverse('email-validate'), content_type='application/json', data=json.dumps(normal_email)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(
            reverse('email-validate'), content_type='application/json', data=json.dumps(invalid_email)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        client = self.register_user_with_data()

        response = client.post(
            reverse('email-validate'), content_type='application/json', data=json.dumps(registered_email)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # social sign_up tests

    def test_social_signup_with_invalid_user_name(self):
        """
        social sign up testing with different codes
        :return:
        """

        social_signup_params = self.social_signup_params.copy()
        social_signup_params.update({"username": "hgdfjgshfv"})
        response = self.client.post(
            reverse('social-signup'), content_type='application/json', data=json.dumps(social_signup_params)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_social_signup_without_first_name(self):
        """
        The function will try social sign up without first name
        :return:
        """

        social_signup_params = self.social_signup_params.copy()
        del social_signup_params['first_name']
        response = self.client.post(
            reverse('social-signup'), content_type='application/json', data=json.dumps(social_signup_params)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_social_signup_without_role(self):
        """
        The function will try social sign up without role
        :return:
        """

        social_signup_params = self.social_signup_params.copy()
        del social_signup_params['role']
        response = self.client.post(
            reverse('social-signup'), content_type='application/json', data=json.dumps(social_signup_params)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_social_signup_existing_celebrity(self):
        """
        Social sign up with registered celebrity
        :return:
        """

        client = self.register_user_with_data(role='celebrity')

        client.post(
            reverse('celebrity_profile'), content_type='application/json', data=json.dumps(self.celebrity_profile_data)
        )

        response = client.post(
            reverse('social-signup'), content_type='application/json', data=json.dumps(self.social_signup_params)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_social_signup_serializer_invalid(self):
        """
        The function will call the social sign up API without required parameter
        :return:
        """

        social_signup_params = self.social_signup_params.copy()
        del social_signup_params["sign_up_source"]
        response = self.client.post(
            reverse('social-signup'), content_type='application/json', data=json.dumps(social_signup_params)
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_logout(self):
        """
        Registered fan is trying to logout
        :return:
        """

        client = self.register_user_with_data()

        response = client.post(
            reverse('logout'), content_type='application/json', data=json.dumps({'registration_id': ''})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # the following functions will test the forgot password API and reset password API

    def test_forgot_password(self):
        """
        Simple case of forgot password
        :return:
        """

        self.register_user_with_data()

        response = self.client.post(
            reverse('forgot-password'), content_type='application/json', data=json.dumps(
                {'email': 'aswinmohan+fan@qburst.com'}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_forgot_password_empty_config(self):
        """
        The function will test forgot password API without the necessary configuration
        :return:
        """

        self.register_user_with_data()

        Config.objects.get(key='sender_email').delete()
        Config.objects.get(key='reset_password_link').delete()
        Config.objects.get(key='web_url').delete()
        Config.objects.get(key='base_url').delete()
        response = self.client.post(
            reverse('forgot-password'), content_type='application/json', data=json.dumps(
                {'email': 'aswinmohan+fan@qburst.com'}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_forgot_password_no_email(self):
        """
        The function will test the forgot password API without any parameter
        :return:
        """

        self.register_user_with_data()

        response = self.client.post(
            reverse('forgot-password'), content_type='application/json', data=json.dumps({})
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_forgot_password_incorrect_email(self):
        """
        Function willtest forgot password with incorrect email
        :return:
        """

        self.register_user_with_data()

        response = self.client.post(
            reverse('forgot-password'), content_type='application/json', data=json.dumps(
                {'email': 'aswinmohan+incorrect@qburst.com'}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password(self):
        """
        The function will call forgot password API and the reset_id stored is user to calling the reset password
        :return:
        """

        self.register_user_with_data()

        self.client.post(
            reverse('forgot-password'), content_type='application/json', data=json.dumps(
                {'email': 'aswinmohan+fan@qburst.com'}
            )
        )
        user = StargramzUser.objects.get(username='aswinmohan+fan@qburst.com')
        response = self.client.post(
            reverse('reset-password'), content_type='application/json',
            data=json.dumps({'reset_id': str(user.reset_id), 'password': 'qburst@123'})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_reset_password_password_none(self):

        self.register_user_with_data()

        self.client.post(
            reverse('forgot-password'), content_type='application/json',
            data=json.dumps({'email': 'aswinmohan@qburst.com'})
        )
        user = StargramzUser.objects.get(username='aswinmohan+fan@qburst.com')
        response = self.client.post(
            reverse('reset-password'), content_type='application/json',
            data=json.dumps({'reset_id': str(user.reset_id)})
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_incorrect_reset_id(self):

        self.register_user_with_data()

        self.client.post(
            reverse('forgot-password'), content_type='application/json',
            data=json.dumps({'email': 'aswinmohan@qburst.com'})
        )
        incorrect_uuid = uuid.uuid4()
        response = self.client.post(
            reverse('reset-password'), content_type='application/json',
            data=json.dumps({'reset_id': str(incorrect_uuid), 'password': 'qburst@123'})
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_invalid_password(self):

        self.register_user_with_data()

        self.client.post(
            reverse('forgot-password'), content_type='application/json',
            data=json.dumps({'email': 'aswinmohan@qburst.com'})
        )
        user = StargramzUser.objects.get(username='aswinmohan+fan@qburst.com')
        response = self.client.post(
            reverse('reset-password'), content_type='application/json',
            data=json.dumps({'reset_id': str(user.reset_id), 'password': '1234'})
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # The following functions will call change password API with different scenarios

    def test_change_password(self):
        """
        The function will call change password API as a fan
        :return:
        """
        client = self.register_user_with_data()

        response = client.post(
            reverse('change-password'), content_type='application/json',
            data=json.dumps({'old_password': 'qburst@123', 'new_password': "qburst@123456"})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_change_password_data_not_provided(self):
        client = self.register_user_with_data()

        response = client.post(
            reverse('change-password'), content_type='application/json',
            data=json.dumps({'old_password': 'qburst@123'})
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_incorrect_old_password(self):
        client = self.register_user_with_data()

        response = client.post(
            reverse('change-password'), content_type='application/json',
            data=json.dumps({'old_password': 'qburst@12', 'new_password': "qburst@123456"})
        )
        data = json.loads(response.content)
        code = data.get("error").get("code")
        self.assertEqual(int(code), OLD_PASSWORD_ERROR_CODE)

    def test_change_password_same_passwords(self):
        client = self.register_user_with_data()

        response = client.post(
            reverse('change-password'), content_type='application/json',
            data=json.dumps({'old_password': 'qburst@123', 'new_password': "qburst@123"})
        )

        data = json.loads(response.content)
        code = data.get("error").get("code")
        self.assertEqual(int(code), NEW_OLD_SAME_ERROR_CODE)

    def test_change_password_invalide_password(self):
        client = self.register_user_with_data()

        response = client.post(
            reverse('change-password'), content_type='application/json',
            data=json.dumps({'old_password': 'qburst@123', 'new_password': "456"})
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_professions(self):
        """
        Simple API which calls the profession listing API
        :return:
        """
        response = self.client.get(reverse('profession'), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_professions(self):
        """
        Simple API call to the filtered profession which returns the parent child profession tree
        :return:
        """
        response = self.client.get('/api/v1/user/filtered_professions/', content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # Following test cases focus the profile image adding API

    def test_profileimages(self):
        """
        normal scenario
        :return:
        """
        client = self.register_user_with_data()

        response = client.post(
                reverse('profile-images'), content_type='application/json',
                data=json.dumps(
                    {
                        "images": ["IMG_1528889181.jpg", "IMG_1528889165.jpg"],
                        "avatar_photo": "IMG_1528889165.jpg",
                        "featured_image": "IMG_1528889181.jpg"
                    }
                )
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_profileimages_avatar_photo_not_in_images(self):
        """
        avatar photo name is not equal to any names in the provided image list
        :return:
        """
        client = self.register_user_with_data()

        response = client.post(
            reverse('profile-images'), content_type='application/json',
            data=json.dumps(
                {
                    "images": ["IMG_1528889181.jpg", "IMG_1528889165.jpg"],
                    "avatar_photo": "IMG_1528889166.jpg",
                    "featured_image": "IMG_1528889181.jpg"
                }
            )
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_remove_profile_images(self):
        """
        This is un-used API which used for deleting images of a user, now its done in profile-image API
        :return:
        """
        client = self.register_user_with_data()

        user = StargramzUser.objects.get(username='aswinmohan+fan@qburst.com')
        user.avatar_photo_id = 1
        user.save()
        ProfileImage.objects.create(user=user, photo='IMG_1528889181.jpg')

        response = client.post(
                reverse('remove-photo'), content_type='application/json',
                data=json.dumps({'id': ['1']})
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_remove_profile_images_id_null(self):
        client = self.register_user_with_data()

        user = StargramzUser.objects.get(username='aswinmohan+fan@qburst.com')
        ProfileImage.objects.create(user=user, photo='IMG_1528889182.jpg')

        response = client.post(
                reverse('remove-photo'), content_type='application/json',
                data=json.dumps({})
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # The following functions will test the notification settings API in different scenarios

    def test_notification_settings(self):
        """
        Simple notification settings API call
        :return:
        """

        notification_settings_params = self.notification_settings_params.copy()

        client = self.register_user_with_data(role='celebrity')

        response = client.post(
            reverse('notification-settings'), content_type='application/json',
            data=json.dumps(notification_settings_params)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_notification_settings_email_already_registered(self):

        notification_settings_params = self.notification_settings_params.copy()
        notification_settings_params.update({"secondary_email": "aswinmohan@qburst.com"})

        client = self.register_user_with_data(role='celebrity')

        response = client.post(
            reverse('notification-settings'), content_type='application/json',
            data=json.dumps(notification_settings_params)
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_notification_settings_no_fields(self):

        client = self.register_user_with_data(role='celebrity')

        response = client.post(
            reverse('notification-settings'), content_type='application/json',
            data=json.dumps({})
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_notification_settings_mobile_verified(self):
        """
        The function will check the special condition where if the mobile verified is true the mobile number cannot
        be changed with this API
        :return:
        """

        client = self.register_user_with_data(role='celebrity')

        user = StargramzUser.objects.get(username='aswinmohan@qburst.com')
        settings = SettingsNotifications.objects.get(user=user)
        settings.mobile_verified = True
        settings.save()

        response = client.post(
            reverse('notification-settings'), content_type='application/json',
            data=json.dumps(self.notification_settings_params)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # Following functions will call user details API

    def test_user_details(self):
        client = self.register_user_with_data(role='celebrity')

        client.post(
            reverse('celebrity_profile'), content_type='application/json', data=json.dumps(self.celebrity_profile_data)
        )

        user = StargramzUser.objects.get(username='aswinmohan@qburst.com')
        vanity = VanityUrl.objects.get(user=user).name

        response = client.get('/api/v1/user/user_details/%s/' % vanity, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_details_wrong_vanity(self):
        celebrity_client = self.register_user_with_data(role='celebrity')
        self.register_user_with_data()

        celebrity_client.post(
            reverse('celebrity_profile'), content_type='application/json', data=json.dumps(self.celebrity_profile_data)
        )

        celebrity = StargramzUser.objects.get(username='aswinmohan@qburst.com')
        vanity_celebrity = VanityUrl.objects.get(user=celebrity).name

        fan = StargramzUser.objects.get(username='aswinmohan+fan@qburst.com')
        vanity_fan = VanityUrl.objects.get(user=fan).name

        response = celebrity_client.get(
            '/api/v1/user/user_details/a%s/' % vanity_celebrity, content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = celebrity_client.get('/api/v1/user/user_details/%s/' % vanity_fan, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_details_user_has_no_vanity(self):
        celebrity_client = self.register_user_with_data(role='celebrity')
        # the condition will send random character as vanity which is not a user
        response = celebrity_client.get(
            '/api/v1/user/user_details/jsdhgfkjhg/', content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # the condition will send primary key as vanity which is not a user
        response = celebrity_client.get(
            '/api/v1/user/user_details/152/', content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_users_details_http_version_greater_than_5(self):

        register_params = self.register_params.copy()
        response = self.client.post(
            reverse('register'), content_type='application/json', data=json.dumps(register_params)
        )
        data = json.loads(response.content)
        token = data.get("data").get("user").get('authentication_token')
        header = self.header.copy()
        header.update({"HTTP_VERSION": "4.5"})
        header.update({"HTTP_AUTHORIZATION": 'token ' + token})
        client = Client(**header)

        user = StargramzUser.objects.get(username='aswinmohan@qburst.com')
        vanity = VanityUrl.objects.get(user=user).name

        response = client.get('/api/v1/user/user_details/%s/' % vanity, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_users_details_user_who_have_group_account(self):
        client = self.register_user_with_data(role='group')
        GroupType.objects.create(group_name='Charity', order=1, active=True)
        client.post(
                reverse('group-account'), content_type='application/json', data=json.dumps(self.group_account_params)
            )
        user = StargramzUser.objects.get(username='aswinmohan+group@qburst.com')
        vanity = VanityUrl.objects.get(user=user).name
        response = client.get('/api/v1/user/user_details/%s/' % vanity, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_users_details_user_retrieve_user_not_exist(self):
        client = self.register_user_with_data(role='celebrity')

        # invalid character as vanity in user_details.get_details
        response = client.get('/api/v1/user/user_details/dsdf/get_details/', content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # invalid character as vanity in user_details.retrieve
        response = client.get('/api/v1/user/user_details/dsdf/', content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_users_details_user_update(self):
        client = self.register_user_with_data(role='celebrity')
        user = StargramzUser.objects.get(username='aswinmohan@qburst.com')
        vanity = VanityUrl.objects.get(user=user).name

        client.post(
            reverse('celebrity_profile'),
            content_type='application/json', data=json.dumps(self.celebrity_profile_data)
                )

        response = client.put(
            '/api/v1/user/user_details/%s/' % vanity, content_type='application/json', data=json.dumps(
                {
                    "user_details": {
                        "first_name": "aswin new",
                        "date_of_birth": "01/24/1995",
                        "show_nick_name": "true",
                        "nick_name": "aswin the celebrity"
                    },
                    "celebrity_details": {
                        "rate": 45,
                        "weekly_limits": 34,
                        "availability": "true",
                        "check_payments": "true"
                    }
                }
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_users_details_user_update_validation_error(self):
        client = self.register_user_with_data(role='celebrity')
        user = StargramzUser.objects.get(username='aswinmohan@qburst.com')
        vanity = VanityUrl.objects.get(user=user).name

        response = client.put(
            '/api/v1/user/user_details/%s/' % vanity, content_type='application/json', data=json.dumps(
                {
                    "user_details": {
                        "first_name": "aswin new",
                        "email": "jhfcjhgfjhgfjh",
                        "date_of_birth": "01/24/2010",
                        "show_nick_name": "true",
                        "nick_name": "aswin the celebrity"
                    }
                }
            )
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # device-token testing

    def test_device_token(self):
        client = self.register_user_with_data(role='fan')
        response = client.post(reverse('device-token'), content_type='application/json', data=json.dumps(
            {
                "device_type": "android",
                "device_token": "token_jkhdfghzgfdkhjdgfksjgh",
                "device_id": "id_jkdhgfsjhgfjshdfguywetuyt"
            }
        ))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_device_validation_error(self):
        client = self.register_user_with_data(role='fan')
        response = client.post(reverse('device-token'), content_type='application/json', data=json.dumps(
            {
                "device_type": "android",
                "device_token": "token_jkhdfghzgfdkhjdgfksjgh"
            }
        ))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Contact support API testing

    def test_contact_support(self):
        client = self.register_user_with_data(role='fan')
        response = client.post(reverse('contact-support'), content_type='application/json', data=json.dumps(
            {
                "comments": "you have a good back-end intern"
            }
        ))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_contact_support(self):
        client = self.register_user_with_data(role='fan')
        response = client.post(reverse('contact-support'), content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # update role API test

    def test_update_role_celebrity_updating_role_to_fan(self):
        client = self.register_user_with_data(role='celebrity')
        client.post(
            reverse('celebrity_profile'),
            content_type='application/json', data=json.dumps(self.celebrity_profile_data)
            )
        response = client.post(reverse('update-role'), content_type='application/json', data=json.dumps(
            {"role": "R1001"}
        ))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_role_fan_updating_role_to_celebrity(self):
        client = self.register_user_with_data(role='fan')
        response = client.post(reverse('update-role'), content_type='application/json', data=json.dumps(
            {"role": "R1002"}
        ))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_role_role_is_not_provided(self):
        client = self.register_user_with_data(role='fan')
        response = client.post(reverse('update-role'), content_type='application/json', data=json.dumps({}))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # update notification badge API test

    def test_update_notification_badge(self):
        client = self.register_user_with_data(role='fan')
        response = client.get(reverse('update-notification-badge-number'), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # alert fan API test

    def test_alert_fan_celebrity_id_is_correct(self):
        client_fan = self.register_user_with_data(role='fan')
        client_celebrity = self.register_user_with_data(role='celebrity')

        client_celebrity.post(
                    reverse('celebrity_profile'),
                    content_type='application/json', data=json.dumps(self.celebrity_profile_data)
                    )
        celebrity = StargramzUser.objects.get(username='aswinmohan@qburst.com')
        response = client_fan.post(
            reverse('alert fan when celebrity available'),
            content_type='application/json',
            data=json.dumps({"celebrity": celebrity.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # existing alert

        response = client_fan.post(
            reverse('alert fan when celebrity available'),
            content_type='application/json',
            data=json.dumps({"celebrity": celebrity.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_alert_fan_incorrect_celebrity_id(self):
        client_fan = self.register_user_with_data(role='fan')
        self.register_user_with_data(role='celebrity')

        celebrity = StargramzUser.objects.get(username='aswinmohan@qburst.com')
        response = client_fan.post(
            reverse('alert fan when celebrity available'),
            content_type='application/json',
            data=json.dumps({"celebrity": celebrity.id}))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # social-signup-validate API test

    def test_social_signup_validate_facebook(self):

        # facebook sign_up_social_test

        social_signup_params = self.social_signup_params.copy()
        social_signup_params.update({"sign_up_source": 2})
        self.client.post(
                reverse('social-signup'), content_type='application/json', data=json.dumps(social_signup_params)
            )

        response = self.client.post(
            reverse('social-signup-validate'), content_type='application/json', data=json.dumps(
                {
                    "signup_source": 2,
                    "social_id": "facebook/5456698/testing/id",
                    "email": "aswinmohan@qburst.com"
                }
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_social_signup_validate_google(self):

        # google sign_up_social_test

        social_signup_params = self.social_signup_params.copy()
        social_signup_params.update({"sign_up_source": 3})
        self.client.post(
                reverse('social-signup'), content_type='application/json', data=json.dumps(social_signup_params)
            )

        response = self.client.post(
            reverse('social-signup-validate'), content_type='application/json', data=json.dumps(
                {
                    "signup_source": 3,
                    "social_id": "facebook/5456698/testing/id",
                    "email": "aswinmohan@qburst.com"
                }
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_social_signup_validate_instagram(self):

        # instagram sign_up_social_test

        social_signup_params = self.social_signup_params.copy()
        social_signup_params.update({"sign_up_source": 4})
        self.client.post(
                reverse('social-signup'), content_type='application/json', data=json.dumps(social_signup_params)
            )

        response = self.client.post(
            reverse('social-signup-validate'), content_type='application/json', data=json.dumps(
                {
                    "signup_source": 4,
                    "social_id": "facebook/5456698/testing/id",
                    "email": "aswinmohan@qburst.com"
                }
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_social_signup_validate_twitter(self):

        # twitter sign_up_social_test

        social_signup_params = self.social_signup_params.copy()
        social_signup_params.update({"sign_up_source": 5})
        self.client.post(
            reverse('social-signup'), content_type='application/json', data=json.dumps(social_signup_params)
        )

        response = self.client.post(
            reverse('social-signup-validate'), content_type='application/json', data=json.dumps(
                {
                    "signup_source": 5,
                    "social_id": "facebook/5456698/testing/id",
                    "email": "aswinmohan@qburst.com"
                }
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_social_signup_validate_exception(self):

        # no user with this email

        response = self.client.post(
            reverse('social-signup-validate'), content_type='application/json', data=json.dumps(
                {
                    "signup_source": 5,
                    "social_id": "facebook/5456698/testing/id",
                    "email": "aswinmohan@qburst.com"
                }
            )
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # field is not provided

        response = self.client.post(
            reverse('social-signup-validate'), content_type='application/json', data=json.dumps({})
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_unseen_count(self):
        client = self.register_user_with_data(role='fan')
        response = client.get(reverse('update-unseen-count'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # signed_url API test

    def test_signed_url(self):
        client = self.register_user_with_data(role='fan')
        response = client.get(reverse('signed-aws-post-url'),
                              data={"extension": "mp4", "key": "authentication_videos", "file_type": "video"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_signed_url_no_params(self):
        client = self.register_user_with_data(role='fan')
        response = client.get(reverse('signed-aws-post-url'), data={})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # get_signed_url API test

    def test_get_signed_url(self):
        client = self.register_user_with_data(role='fan')
        response = client.get(reverse('signed-aws-get-url'),
                              data={"key": "authentication_videos", "file_name": "the_file"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # key is not in the choice field

    def test_get_signed_url_invalid_key(self):
        client = self.register_user_with_data(role='fan')
        response = client.get(reverse('signed-aws-get-url'),
                              data={"key": "fgdfgdfgd", "file_name": "the_file"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # social media url API test

    def test_social_media_url(self):
        client = self.register_user_with_data(role='fan')
        response = client.post(reverse('social-links'),
                               content_type='application/json',
                               data=json.dumps(
                                   {
                                       "facebook_url": "https://facebook.com/home",
                                       "google_url": "https://google.com/home",
                                       "instagram_url": "https://instagram.com/home",
                                       "twitter_url": "https://twitter.com/home"
                                   }
                               ))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_social_media_url_with_incorrect_data(self):
        client = self.register_user_with_data(role='fan')
        response = client.post(reverse('social-links'),
                               content_type='application/json',
                               data=json.dumps({
                                   "facebook_url": "hkjfkhjfhjfkhj"
                               }))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
