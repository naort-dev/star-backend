from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status
import json
from urllib.parse import urlencode
from payments.models import StarsonaTransaction
from config.models import Config
from stargramz.models import StargramVideo, Stargramrequest, Reaction
from users.models import ProfileImage
from hashids import Hashids
hashids = Hashids(min_length=8)

class StargramzTest(TestCase):
    """
        Unit test file for testing Starsona Bookings and listing
    """
    fixtures = ['relations.json', 'occasions.json', 'orderrelations.json', 'profession.json', 'roles.json',
                'config.json']

    def setUp(self):
        self.client = Client(HTTP_DEVICE='web', HTTP_VERSION='1.0')

    def test_occasions(self):
        """
            Test occasions get api
        """
        response = self.client.get(reverse('occasion_list'), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_relationships(self):
        """
            Adding new relationship via API
        """
        params = json.dumps({'other': 'My-test-relations'})
        response = self.client.post(
            reverse('other_relation'),
            data=params, content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_relationships_with_wrong_params(self):
        """
            Test other relation with invalid parameters
        """
        params = json.dumps({'others': 'My-test-relations'})
        response = self.client.post(
            reverse('other_relation'),
            data=params, content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_relationships_with_other_as_boolean(self):
        """
            Test other relations api with arguments with a boolean
        """
        params = json.dumps({'other': True})
        response = self.client.post(
            reverse('other_relation'),
            data=params, content_type='application/json'
        )
        data = json.loads(response.content.decode('utf8'))
        self.assertEqual(data['error']['message'], 'Field should be string.')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_relationships_with_empty_params(self):
        """
            Test the other relations API with empty params
        """
        params = json.dumps({})
        response = self.client.post(
            reverse('other_relation'),
            data=params, content_type='application/json'
        )
        data = json.loads(response.content.decode('utf8'))
        self.assertEqual(data['error']['message'], 'Other Field is Required')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_first_booking_without_auth_token(self):
        """
            Test bookings API without auth token details
        """

        params = {"occasion": 1}
        response = self.client.post(
            '/api/v1/request/stargramz/',
            data=params,
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def create_celebrity_user(self):
        """
            Creating celebrity users with celebrity details and profile images
        :return: Celebrity details
        """
        params = json.dumps({
            "first_name":"Akhilraj",
            "last_name": "NS",
            "password":"qburst@123",
            "email": "akhilns@qburst.com",
            "role": "R1002",
            "referral_code": ""
        })
        response = self.client.post(
            reverse('register'),
            data=params, content_type='application/json'
        )
        data = json.loads(response.content.decode('utf8'))
        token = data['data']['user']['authentication_token']
        celebrity_params = json.dumps({
            "rate": "100.00",
            "weekly_limits": 10,
            "profession": ["2", "12"],
            "profile_video": "home/key/key.mp4",
            "availability": True,
            'description': "I am superstar",
            'charity': "Well funded"
        })
        celebrity = self.client.post(
            reverse('celebrity_profile'),
            **{'HTTP_AUTHORIZATION': 'token %s' % token},
            data=celebrity_params, content_type='application/json'
        )

        images = json.dumps({
            "images": ["sample1.jpg", "sample2.jpg"],
            "avatar_photo": "sample1.jpg",
            "featured_image": "sample2.jpg"
        })
        profile_images = self.client.post(
            reverse('profile-images'),
            **{'HTTP_AUTHORIZATION': 'token %s' % token},
            data=images, content_type='application/json'
        )

        self.assertEqual(profile_images.status_code, status.HTTP_200_OK)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(celebrity.status_code, status.HTTP_200_OK)
        return data['data']['user']

    def create_a_fan_account(self, fan='fan'):
        """
        Create a fan user with dynamic emails
        :param fan:
        :return:
        """
        params = json.dumps({
            "first_name": "Akhilraj",
            "last_name": "NS",
            "password": "qburst@123",
            "email": "akhilns+%s@qburst.com" % fan,
            "role": "R1001",
            "referral_code": ""
        })
        response = self.client.post(
            reverse('register'),
            data=params, content_type='application/json'
        )
        data = json.loads(response.content.decode('utf8'))
        return data['data']['user']

    def generate_stripe_customer_record(self, token):
        """
            Generate the stripe customer record details for making stripe payments
        """
        params = json.dumps({
            "api_key": "2017-08-15"
        })
        response = self.client.post(
            reverse('generate-customer-key'),
            **{'HTTP_AUTHORIZATION': 'token %s' % token},
            data=params, content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def create_booking_request(self, celebrity_id, token, occasion=4, request_type=1):
        """
            Creating a booking with changable occasion and request type
        """
        request_details = json.dumps({
            "stargramto": "Akhilraj",
            "stargramfrom": "Akhil",
            "relationship": {"id": 2, "title": "mother"},
            "show_relationship": True,
            "date": "12/24/2019"
        })

        params = {
            "celebrity": celebrity_id,
            "request_type": request_type,
            "occasion": occasion,
            "request_details": request_details,
            "public_request": True,
            "from_audio_file": "",
            "to_audio_file": ""
        }
        response = self.client.post(
            '/api/v1/request/stargramz/',
            **{'HTTP_AUTHORIZATION': 'token %s' % token},
            data=params,
        )
        return response, json.loads(response.content.decode('utf8'))

    def test_to_create_a_new_request_booking_feature(self):
        """
        Test to create a normal booking flow without payments
        """
        fan_details = self.create_a_fan_account()
        celebrity_details = self.create_celebrity_user()
        token = fan_details['authentication_token']
        response, data = self.create_booking_request(celebrity_details['id'], token)
        title = 'Bar/Bat Mitzvah video shout-out from Akhilraj Ns'
        self.assertEqual(title, data['data']['stargramz_response']['booking_title'])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_to_create_a_request_booking_with_invalid_occasion_invalid_fan(self):
        """
        Test Request bookings with invalid occasions and celebritydetails
        :return:
        """
        fan_details = self.create_a_fan_account()
        token = fan_details['authentication_token']

        request_details = json.dumps({
            "stargramto": "Akhilraj",
            "stargramfrom": "Akhil",
            "relationship": {"id": 2, "title": "mother"},
            "show_relationship": True,
            "date": "12/24/2019"
        })

        params = {
            "celebrity": 3,
            "request_type": 1,
            "occasion": 66,
            "request_details": request_details,
            "public_request": True,
            "from_audio_file": "",
            "to_audio_file": ""
        }
        response = self.client.post(
            '/api/v1/request/stargramz/',
            **{'HTTP_AUTHORIZATION': 'token %s' % token},
            data=params,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_to_update_existing_request_booking_feature(self):
        """
            Test to update an existing booking with in the booking edit limit
        """
        fan_details = self.create_a_fan_account()
        celebrity_details = self.create_celebrity_user()
        token = fan_details['authentication_token']

        request_details = json.dumps({
            "stargramto": "Akhilraj",
            "stargramfrom": "Akhil",
            "relationship": {"id": 2, "title": "mother"},
            "show_relationship": True,
            "date": "12/24/2019"
        })

        response, data = self.create_booking_request(celebrity_details['id'], token, occasion=5, request_type=2)
        title = 'Birthday announcement from Akhilraj Ns'
        self.assertEqual(title, data['data']['stargramz_response']['booking_title'])

        new_params = urlencode({
            "celebrity": celebrity_details['id'],
            "request_type": 2,
            "occasion": 4,
            "request_details": request_details,
        })

        update_response = self.client.put(
            '/api/v1/request/stargramz/%d/' % int(data['data']['stargramz_response']['id']),
            **{'HTTP_AUTHORIZATION': 'token %s' % token},
            data=new_params,
            content_type='application/x-www-form-urlencoded'
        )
        title = 'Bar/Bat Mitzvah announcement from Akhilraj Ns'
        data = json.loads(update_response.content.decode('utf8'))
        self.assertEqual(title, data['data']['stargramz_response']['booking_title'])
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)

    def test_update_booking_with_invalid_celebrity(self):
        """
            Test to update the booking with an invalid celebrity details
        """
        fan_details = self.create_a_fan_account()
        celebrity_details = self.create_celebrity_user()
        token = fan_details['authentication_token']

        request_details = json.dumps({
            "stargramto": "Akhilraj",
            "stargramfrom": "Akhil",
            "relationship": {"id": 2, "title": "mother"},
            "show_relationship": True,
            "date": "12/24/2019"
        })

        response, data = self.create_booking_request(celebrity_details['id'], token, occasion=5, request_type=2)
        title = 'Birthday announcement from Akhilraj Ns'
        self.assertEqual(title, data['data']['stargramz_response']['booking_title'])

        new_params = urlencode({
            "celebrity": 66,
            "request_type": 2,
            "occasion": 4,
            "request_details": request_details,
        })

        update_response = self.client.put(
            '/api/v1/request/stargramz/%d/' % int(data['data']['stargramz_response']['id']),
            **{'HTTP_AUTHORIZATION': 'token %s' % token},
            data=new_params,
            content_type='application/x-www-form-urlencoded'
        )

        self.assertEqual(update_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_booking_with_invalid_occasion(self):
        """
            Test to update booking with invalid occasion
        """
        fan_details = self.create_a_fan_account()
        celebrity_details = self.create_celebrity_user()
        token = fan_details['authentication_token']

        request_details = json.dumps({
            "stargramto": "Akhilraj",
            "stargramfrom": "Akhil",
            "relationship": {"id": 2, "title": "mother"},
            "show_relationship": True,
            "date": "12/24/2019"
        })

        response, data = self.create_booking_request(celebrity_details['id'], token, occasion=5, request_type=2)
        title = 'Birthday announcement from Akhilraj Ns'
        self.assertEqual(title, data['data']['stargramz_response']['booking_title'])

        new_params = urlencode({
            "celebrity": celebrity_details['id'],
            "request_type": 2,
            "occasion": 109,
            "request_details": request_details,
        })

        update_response = self.client.put(
            '/api/v1/request/stargramz/%d/' % int(data['data']['stargramz_response']['id']),
            **{'HTTP_AUTHORIZATION': 'token %s' % token},
            data=new_params,
            content_type='application/x-www-form-urlencoded'
        )

        self.assertEqual(update_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_request_booking_with_invalid_booking_id(self):
        """
            Test the update bookings api with invalid booking ID
        """
        fan_details = self.create_a_fan_account()
        celebrity_details = self.create_celebrity_user()
        token = fan_details['authentication_token']

        request_details = json.dumps({
            "stargramto": "Akhilraj",
            "stargramfrom": "Akhil",
            "relationship": {"id": 2, "title": "mother"},
            "show_relationship": True,
            "date": "12/24/2019"
        })

        response, data = self.create_booking_request(celebrity_details['id'], token, occasion=5, request_type=2)
        title = 'Birthday announcement from Akhilraj Ns'
        self.assertEqual(title, data['data']['stargramz_response']['booking_title'])

        new_params = urlencode({
            "celebrity": celebrity_details['id'],
            "request_type": 2,
            "occasion": 4,
            "request_details": request_details,
        })

        update_response = self.client.put(
            '/api/v1/request/stargramz/%d/' % int(999),
            **{'HTTP_AUTHORIZATION': 'token %s' % token},
            data=new_params,
            content_type='application/x-www-form-urlencoded'
        )
        self.assertEqual(update_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_new_request_booking_and_retrieve_the_details(self):
        """
            Test to validate the bookings retrieve details
        """
        fan_details = self.create_a_fan_account()
        celebrity_details = self.create_celebrity_user()
        token = fan_details['authentication_token']

        response, data = self.create_booking_request(celebrity_details['id'], token, occasion=4, request_type=1)
        get_response = self.client.get(
            '/api/v1/request/stargramz/%d/' % int(data['data']['stargramz_response']['id']),
            **{'HTTP_AUTHORIZATION': 'token %s' % token}
        )

        get_data = json.loads(get_response.content.decode('utf8'))

        title = 'Bar/Bat Mitzvah video shout-out from Akhilraj Ns'
        self.assertEqual(title, data['data']['stargramz_response']['booking_title'])
        self.assertEqual(title, get_data['data']['stargramz_response']['booking_title'])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)

    def test_request_booking_and_retrieve_with_invalid_user(self):
        """
            Test to retrieve request booking details with invalid user not the requester fan/ requested celebrity
        """
        fan_details = self.create_a_fan_account()
        celebrity_details = self.create_celebrity_user()
        token = fan_details['authentication_token']

        response, data = self.create_booking_request(celebrity_details['id'], token, occasion=4, request_type=1)
        fan_details2 = self.create_a_fan_account(fan=2)
        token2 = fan_details2['authentication_token']
        get_response = self.client.get(
            '/api/v1/request/stargramz/%d/' % int(data['data']['stargramz_response']['id']),
            **{'HTTP_AUTHORIZATION': 'token %s' % token2}
        )

        title = 'Bar/Bat Mitzvah video shout-out from Akhilraj Ns'
        self.assertEqual(title, data['data']['stargramz_response']['booking_title'])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_response.status_code, status.HTTP_400_BAD_REQUEST)

    def add_video_to_booking(self, booking_id):
        """
            Function to add the video bookings and update the booking to complete
        """
        Stargramrequest.objects.filter(pk=booking_id).update(request_status=6)
        video = StargramVideo.objects.create(
            stragramz_request_id=booking_id,
            video='sample.mp4',
            thumbnail='thumbnail_sample.jpg',
            duration='10:00',
            read_status=True,
            status=1,
            width=400,
            height=400
        )
        return hashids.encode(video.pk)

    def add_reactions(self, booking_id, fan_id):
        """
            Adding new reactions record
        """
        reactions = Reaction.objects.create(
            booking_id=booking_id,
            user_id=fan_id,
            file_type=1,
            reaction_file='reactions.jpg',
            file_thumbnail='reactions_thumb.jpg'
        )
        return hashids.encode(reactions.pk)

    def test_booking_with_transactions_completed(self):
        """
            Test the request booking with all the details
        """
        fan_details = self.create_a_fan_account()
        celebrity_details = self.create_celebrity_user()
        token = fan_details['authentication_token']
        Config.objects.filter(key='booking_edit_time').update(value=0)

        request_details = json.dumps({
            "stargramto": "Akhilraj",
            "stargramfrom": "Akhil",
            "relationship": {"id": 2, "title": "mother"},
            "show_relationship": True,
            "date": "12/24/2019"
        })

        response, data = self.create_booking_request(celebrity_details['id'], token, occasion=4, request_type=1)
        StarsonaTransaction.objects.create(
            starsona_id=data['data']['stargramz_response']['id'],
            fan_id=fan_details['id'],
            celebrity_id=celebrity_details['id'],
            amount=10,
            transaction_status=2,
            source_id='src_1D1676ECTOB5aCAKdP6IzLTi'
        )

        new_params = urlencode({
            "celebrity": celebrity_details['id'],
            "request_type": 2,
            "occasion": 4,
            "request_details": request_details,
        })

        update_response = self.client.put(
            '/api/v1/request/stargramz/%d/' % int(data['data']['stargramz_response']['id']),
            **{'HTTP_AUTHORIZATION': 'token %s' % token},
            data=new_params,
            content_type='application/x-www-form-urlencoded'
        )
        data_update = json.loads(update_response.content.decode('utf8'))
        title = 'Bar/Bat Mitzvah video shout-out from Akhilraj Ns'
        error_msg = 'Sorry; You can no longer update this request, as we have started processing it'

        self.assertEqual(error_msg, data_update['error']['message'])
        self.assertEqual(update_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(title, data['data']['stargramz_response']['booking_title'])
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_booking_with_transactions_completed_to_get_filtered(self):
        """
            Test the requests listing API to list all the completed bookings
        """
        fan_details = self.create_a_fan_account()
        celebrity_details = self.create_celebrity_user()
        token = fan_details['authentication_token']

        response, data = self.create_booking_request(celebrity_details['id'], token, occasion=4, request_type=1)
        StarsonaTransaction.objects.create(
            starsona_id=data['data']['stargramz_response']['id'],
            fan_id=fan_details['id'],
            celebrity_id=celebrity_details['id'],
            amount=10,
            transaction_status=3,
            source_id='src_1D1676ECTOB5aCAKdP6IzLTi'
        )

        self.add_video_to_booking(data['data']['stargramz_response']['id'])
        req_params = {"status": "2,3,6"}
        response = self.client.get(
            '/api/v1/request/request_list/',
            **{'HTTP_AUTHORIZATION': 'token %s' % token},
            data=req_params,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_request_list_with_celebrity_token_details(self):
        """
            List the bookings which are assigned to a celebrity
        """
        fan_details = self.create_a_fan_account()
        celebrity_details = self.create_celebrity_user()
        token = fan_details['authentication_token']

        response, data = self.create_booking_request(celebrity_details['id'], token, occasion=4, request_type=1)
        StarsonaTransaction.objects.create(
            starsona_id=data['data']['stargramz_response']['id'],
            fan_id=fan_details['id'],
            celebrity_id=celebrity_details['id'],
            amount=10,
            transaction_status=3,
            source_id='src_1D1676ECTOB5aCAKdP6IzLTi'
        )
        video_id = self.add_video_to_booking(data['data']['stargramz_response']['id'])

        cel_token = celebrity_details['authentication_token']
        req_params = {"status": "all"}
        request_list_response = self.client.get(
            '/api/v1/request/request_list/',
            **{'HTTP_AUTHORIZATION': 'token %s' % cel_token},
            data=req_params,
        )
        title = 'Bar/Bat Mitzvah video shout-out from Akhilraj Ns'
        req_list_data = json.loads(request_list_response.content.decode('utf8'))
        self.assertEqual(title, req_list_data['data']['request_list'][0]['booking_title'])
        self.assertEqual(request_list_response.status_code, status.HTTP_200_OK)

    def test_video_feed_api(self):
        """
            Test the video feed api to list all the public video
        """
        fan_details = self.create_a_fan_account()
        celebrity_details = self.create_celebrity_user()
        token = fan_details['authentication_token']

        response, data = self.create_booking_request(celebrity_details['id'], token, occasion=4, request_type=1)
        StarsonaTransaction.objects.create(
            starsona_id=data['data']['stargramz_response']['id'],
            fan_id=fan_details['id'],
            celebrity_id=celebrity_details['id'],
            amount=10,
            transaction_status=3,
            source_id='src_1D1676ECTOB5aCAKdP6IzLTi'
        )

        video_id = self.add_video_to_booking(data['data']['stargramz_response']['id'])
        cel_token = celebrity_details['authentication_token']
        req_params = {"request_type": 1, "user_id": celebrity_details['id']}
        feed_response = self.client.get(
            '/api/v1/request/featured_videos/',
            **{'HTTP_AUTHORIZATION': 'token %s' % cel_token},
            data=req_params,
        )

        title = 'Bar/Bat Mitzvah video shout-out from Akhilraj Ns'
        req_list_data = json.loads(feed_response.content.decode('utf8'))
        self.assertEqual(title, req_list_data['data']['featured_videos'][0]['booking_title'])
        self.assertEqual(feed_response.status_code, status.HTTP_200_OK)

    def test_video_feed_api_for_todays_video(self):
        """
            Test to filter the video feed API to list all the videos based on dates/months/years
        """
        fan_details = self.create_a_fan_account()
        celebrity_details = self.create_celebrity_user()
        token = fan_details['authentication_token']

        response, data = self.create_booking_request(celebrity_details['id'], token, occasion=4, request_type=1)
        StarsonaTransaction.objects.create(
            starsona_id=data['data']['stargramz_response']['id'],
            fan_id=fan_details['id'],
            celebrity_id=celebrity_details['id'],
            amount=10,
            transaction_status=3,
            source_id='src_1D1676ECTOB5aCAKdP6IzLTi'
        )
        video_id = self.add_video_to_booking(data['data']['stargramz_response']['id'])
        cel_token = celebrity_details['authentication_token']
        req_params = {"date": "today"}
        feed_response = self.client.get(
            '/api/v1/request/featured_videos/',
            **{'HTTP_AUTHORIZATION': 'token %s' % cel_token},
            data=req_params,
        )
        title = 'Bar/Bat Mitzvah video shout-out from Akhilraj Ns'
        self.assertEqual(feed_response.status_code, status.HTTP_200_OK)

        req_params = {"date": "last_7_days"}
        feed_response_7_days = self.client.get(
            '/api/v1/request/featured_videos/',
            **{'HTTP_AUTHORIZATION': 'token %s' % cel_token},
            data=req_params,
        )

        self.assertEqual(feed_response_7_days.status_code, status.HTTP_200_OK)
        req_list_data = json.loads(feed_response_7_days.content.decode('utf8'))
        self.assertEqual(title, req_list_data['data']['featured_videos'][0]['booking_title'])

        req_params = {"date": "this_month", "id": data['data']['stargramz_response']['id']}
        feed_response_this_month = self.client.get(
            '/api/v1/request/featured_videos/',
            **{'HTTP_AUTHORIZATION': 'token %s' % cel_token},
            data=req_params,
        )

        req_list_data = json.loads(feed_response_this_month.content.decode('utf8'))
        self.assertEqual(title, req_list_data['data']['featured_videos'][0]['booking_title'])
        self.assertEqual(feed_response_this_month.status_code, status.HTTP_200_OK)

        req_params = {"date": "this_year", "user_id": celebrity_details['user_id'], "name": "Akhilraj"}
        feed_response_this_year = self.client.get(
            '/api/v1/request/featured_videos/',
            **{'HTTP_AUTHORIZATION': 'token %s' % cel_token},
            data=req_params,
        )

        req_list_data = json.loads(feed_response_this_year.content.decode('utf8'))
        self.assertEqual(title, req_list_data['data']['featured_videos'][0]['booking_title'])
        self.assertEqual(feed_response_this_year.status_code, status.HTTP_200_OK)

    def test_celebrity_profile_page_web(self):
        """
            Test the profile web page URL
        """
        celebrity_details = self.create_celebrity_user()
        ProfileImage.objects.update(thumbnail='thumb.jpg')
        response = self.client.get(
            reverse('profile-details', kwargs={'user_id': celebrity_details['user_id']}),
        )
        self.assertContains(response, '<span style="color:#ffffff; font-weight:500; font-size: 1em;">Get your personalized video from your favorite celebrity</span>',status_code=200)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_play_video_webpage(self):
        """
            Test the video playing web page
        """
        fan_details = self.create_a_fan_account()
        celebrity_details = self.create_celebrity_user()
        token = fan_details['authentication_token']

        response, data = self.create_booking_request(celebrity_details['id'], token, occasion=4, request_type=1)
        StarsonaTransaction.objects.create(
            starsona_id=data['data']['stargramz_response']['id'],
            fan_id=fan_details['id'],
            celebrity_id=celebrity_details['id'],
            amount=10,
            transaction_status=3,
            source_id='src_1D1676ECTOB5aCAKdP6IzLTi'
        )

        video_id = self.add_video_to_booking(data['data']['stargramz_response']['id'])
        video_response = self.client.get(
            reverse('play-video', kwargs={"id": video_id}),
        )
        self.assertContains(video_response, '<video id="my-video" class="video-js col-md-12 vjs-big-play-centered" controls preload="auto" width="640" height="400"', status_code=200)
        self.assertEqual(video_response.status_code, status.HTTP_200_OK)

    def test_play_video_with_invalid_id(self):
        """
            Test the video playing page with invalid video ID
        """
        video_response = self.client.post(
            reverse('play-video', kwargs={"id": 12345678}),
        )
        self.assertContains(video_response, '<h1>404 <br/>No video related to the link was found</h1>',status_code=200)
        self.assertEqual(video_response.status_code, status.HTTP_200_OK)

    def test_play_reaction_video(self):
        """
            Test to play the reaction video
        """
        fan_details = self.create_a_fan_account()
        celebrity_details = self.create_celebrity_user()
        token = fan_details['authentication_token']

        response, data = self.create_booking_request(celebrity_details['id'], token, occasion=4, request_type=1)
        reaction_id = self.add_reactions(data['data']['stargramz_response']['id'], fan_details['id'])
        video_response = self.client.get(
            reverse('play-reaction-video', kwargs={"id": reaction_id}),
        )
        self.assertContains(video_response, '<span class="starsonabanner-title">Starsona</span>', status_code=200)
        self.assertEqual(video_response.status_code, status.HTTP_200_OK)

    def test_play_reaction_video_invalid_id(self):
        """
            Test the web page for reaction files with invalid ID
        """
        video_response = self.client.post(
            reverse('play-reaction-video', kwargs={"id": 12345678}),
        )
        self.assertContains(video_response, '<h1 style="color:#c38d7c;">404</h1>', status_code=200)
        self.assertEqual(video_response.status_code, status.HTTP_200_OK)

    def test_starsona_video_get_api(self):
        """
            API to retrieve all the details of a video
        """
        fan_details = self.create_a_fan_account()
        celebrity_details = self.create_celebrity_user()
        token = fan_details['authentication_token']

        response, data = self.create_booking_request(celebrity_details['id'], token, occasion=4, request_type=1)
        StarsonaTransaction.objects.create(
            starsona_id=data['data']['stargramz_response']['id'],
            fan_id=fan_details['id'],
            celebrity_id=celebrity_details['id'],
            amount=10,
            transaction_status=3,
            source_id='src_1D1676ECTOB5aCAKdP6IzLTi'
        )
        video_id = self.add_video_to_booking(data['data']['stargramz_response']['id'])
        response_video = self.client.get(
            '/api/v1/request/stargramz_video/%s/get/' % video_id,
        )
        video_data = json.loads(response_video.content.decode('utf8'))
        title = 'Bar/Bat Mitzvah video shout-out from Akhilraj Ns'
        self.assertEqual(title, video_data['data']['starsona_video'][0]['booking_title'])
        self.assertEqual(response_video.status_code, status.HTTP_200_OK)

    def test_starsona_video_get_with_video_not_found(self):
        """
            Test the starsona video with invalid video ID
        """
        response_video = self.client.get(
            '/api/v1/request/stargramz_video/%s/get/' % '2q',
        )
        self.assertEqual(response_video.status_code, status.HTTP_400_BAD_REQUEST)

    def test_starsona_video_get_api_without_completed_video(self):
        """
            Test to get the video of an in completed booking request
        """
        fan_details = self.create_a_fan_account()
        celebrity_details = self.create_celebrity_user()
        token = fan_details['authentication_token']

        response, data = self.create_booking_request(celebrity_details['id'], token, occasion=4, request_type=1)
        StarsonaTransaction.objects.create(
            starsona_id=data['data']['stargramz_response']['id'],
            fan_id=fan_details['id'],
            celebrity_id=celebrity_details['id'],
            amount=10,
            transaction_status=3,
            source_id='src_1D1676ECTOB5aCAKdP6IzLTi'
        )
        video_id = self.add_video_to_booking(data['data']['stargramz_response']['id'])
        Stargramrequest.objects.filter(pk=data['data']['stargramz_response']['id']).update(request_status=4)
        response_video = self.client.get(
            '/api/v1/request/stargramz_video/%s/get/' % video_id,
        )
        self.assertEqual(response_video.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_new_comments(self):
        """
            Test to add new comments to a video
        """
        fan_details = self.create_a_fan_account()
        celebrity_details = self.create_celebrity_user()
        token = fan_details['authentication_token']
        response, data = self.create_booking_request(celebrity_details['id'], token, occasion=4, request_type=1)
        StarsonaTransaction.objects.create(
            starsona_id=data['data']['stargramz_response']['id'],
            fan_id=fan_details['id'],
            celebrity_id=celebrity_details['id'],
            amount=10,
            transaction_status=3,
            source_id='src_1D1676ECTOB5aCAKdP6IzLTi'
        )
        video_id = self.add_video_to_booking(data['data']['stargramz_response']['id'])

        params = json.dumps({'comments': 'Superb video', 'video': video_id, 'reply': ''})
        response_comments = self.client.post(
            reverse('comments'),
            data=params, content_type='application/json',
            ** {'HTTP_AUTHORIZATION': 'token %s' % token}
        )
        comments_data = json.loads(response_comments.content.decode('utf8'))

        list_comments = self.client.get(
            reverse('comment-details', kwargs={'pk': video_id}),
            content_type='application/json',
        )
        list_comments_more = self.client.get(
            reverse('comment-details', kwargs={'pk': video_id}),
            data={'last_comment': 1},
            content_type='application/json',
        )

        comments_list_data = json.loads(list_comments.content.decode('utf8'))
        list_comments_more_data = json.loads(list_comments_more.content.decode('utf8'))
        self.assertEqual('Added the comments', comments_data['data']['comments'])
        self.assertEqual('Superb video', comments_list_data['data']['comment_list'][0]['comments'])
        self.assertEqual(response_comments.status_code, status.HTTP_200_OK)
        self.assertEqual(list_comments.status_code, status.HTTP_200_OK)
        self.assertEqual(list_comments_more.status_code, status.HTTP_200_OK)
        self.assertEqual(0, list_comments_more_data['data']['count'])

    def test_add_new_comments_with_validation_error(self):
        """
            Test to verify the validation errors in comments adding
        """
        fan_details = self.create_a_fan_account()
        token = fan_details['authentication_token']

        params = json.dumps({'comments': 'Superb video', 'reply': ''})
        response_comments = self.client.post(
            reverse('comments'),
            data=params, content_type='application/json',
            ** {'HTTP_AUTHORIZATION': 'token %s' % token}
        )
        self.assertEqual(response_comments.status_code, status.HTTP_404_NOT_FOUND)

