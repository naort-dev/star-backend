from locust import Locust, HttpLocust, TaskSet, task, seq_task
import sys

def safe_name(name):
    return name.replace('-', '_').replace('.', '_')

class Struct(object):

    def __init__(self, data):
        for name, value in data.items():
            setattr(self, safe_name(name), self._wrap(value))

    def _wrap(self, value):
        if isinstance(value, (tuple, list, set, frozenset)):
            return type(value)([self._wrap(v) for v in value])
        else:
            return Struct(value) if isinstance(value, dict) else value


class UserBehavior(TaskSet):
    def on_start(self):
        self.locust.headers = dict(
            version='1.0',
            device='web'
        )
        self.username = 'phil.peshin@gmail.com'
        self.password = 'action2!'
        self.config(setup=True)
        self.login(setup=True)
        self.profile()
        self.filtered_professions()

    def on_stop(self):
        pass

    @task
    def config(self, setup = False):
        r = self.client.get('/api/v1/config/', headers=self.locust.headers, allow_redirects=False)
        tmp = Struct(r.json()).data.config
        if setup:
            self.locust.config = tmp


    @task
    def login(self, setup = False):
        params = dict(username=self.username, password=self.password)
        r = self.client.post('/api/v1/user/login/', data=params, headers=self.locust.headers, allow_redirects=False)
        tmp = Struct(r.json()).data.user
        if setup:
            self.locust.user = tmp
            self.locust.headers['Authorization'] = 'Token ' + self.locust.user.authentication_token

    @task
    def profile(self):
        with self.client.get('/api/v1/user/user_details/%s/' % str(self.locust.user.id),
                             headers=self.locust.headers, allow_redirects=False, catch_response=True, name='/api/v1/user/user_details') as response:
            user = Struct(response.json()).data.user
            if user.id != self.locust.user.id:
                response.failure("Incorrect user details")

    @task
    def filtered_professions(self):
        with self.client.get('/api/v1/user/filtered_professions/', headers=self.locust.headers, allow_redirects=False, catch_response=True) as response:
            self.locust.filtered_professions = Struct(response.json()).data.filtered_professions
            if len(self.locust.filtered_professions) <= 0:
                response.failure("No filtered professions")

    @task
    class FeaturedVideos(TaskSet):
        def featured_videos(self, offset):
            with self.client.get('/api/v1/request/featured_videos/?offset=%d&request_type=1&name=' % offset,
                                 headers=self.locust.headers, allow_redirects=False, catch_response=True, name='/api/v1/request/featured_videos') as response:
                featured_videos = Struct(response.json()).data.featured_videos
                if len(featured_videos) <= 0:
                    response.failure("No featured videos")
                for video in featured_videos:
                    self.check_video(video)

        def check_video(self, video):
            with self.client.get(video.s3_video_url, headers=self.locust.headers, allow_redirects=False, catch_response=True, name='/private/video') as response:
                if not(response.is_redirect and response.headers['location'].index('s3.amazonaws.com') >= 0):
                    response.failure("Got wrong response from /private/video")

        @task
        def featured_videos_scroll(self):
            for offset in [0, 10, 20]:
                self.featured_videos(offset)
            self.interrupt()

    @task
    class CelebrityList(TaskSet):
        def celebrity_list(self, offset):
            with self.client.get('/api/v1/user/fan/celebrity_list/get_list/?name=&profession=&offset=%d&sort=featured' % offset,
                                 headers=self.locust.headers, allow_redirects=False, catch_response=True, name='/api/v1/user/fan/celebrity_list/get_list') as response:
                celebrity_list = Struct(response.json()).data.celebrity_list
                if len(celebrity_list) <= 0:
                    response.failure("Celebrity list empty")

        @task
        def celebrity_list_scroll(self):
            for offset in [0, 10, 20]:
                self.celebrity_list(offset)
            self.interrupt()


class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    min_wait = 1000
    max_wait = 5000

if __name__ == '__main__':
    Locust.host = sys.argv[1]
    WebsiteUser().run()