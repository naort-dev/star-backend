INPUT_DATE_FORMAT = ["%m/%d/%Y"]
OUTPUT_DATE_FORMAT = "%d/%m/%Y"
OUTPUT_DATETIME_FORMAT = "%d/%m/%Y %H:%M:%S"


class K:
    def __init__(self, label=None, **kwargs):
        assert(len(kwargs) == 1)
        for k, v in kwargs.items():
            self.id = k
            self.v = v
        self.label = label or self.id


class Konstants:
    def __init__(self, *args):
        self.klist = args
        for k in self.klist:
            setattr(self, k.id, k.v)

    def choices(self):
        return [(k.v, k.label) for k in self.klist]

    def get_label(self, key):
        for k in self.klist:
            if k.v == key:
                return k.label
        return None

    def get_keys(self):
        list_keys = list(self.__dict__.keys())
        list_keys.remove("klist")
        return list_keys

    def get_key_values(self):
        return [k.v for k in self.klist]

    def get_all_labels(self):
        return [k.label for k in self.klist]


ROLES = Konstants(
    K(fan='R1001', label='Fan'),
    K(celebrity='R1002', label='Celebrity'),
    K(admin='R1003', label='Admin'),
    K(group_account='R1004', label='Group Account'),
    K(reviwer='R1005', label='Reviewer'),
    K(watcher='R1006', label='Watcher')
)


CELEBRITY_CATEGORIES = Konstants(
    K(music='CC1001', label='Music'),
    K(actor='CC1002', label='Actor'),
    K(model='CC1003', label='Model'),
    K(sports='CC1004', label='Sports')
)


FEATURES = Konstants(
    K(user_profile_retrieve='F1001', label='User Profile Retrieve'),
    K(celebrity_retrieve='F1002', label='Celebrity Retrieve'),
    K(fan_request_list='F1003', label='Fan Request List'),
    K(fan_request_retrieve='F1004', label='Fan Request Retrieve'),
    K(profile_image_URL_add='F1005', label='Profile Image URL Add'),
    K(user_profile_update='F1006', label='User Profile Update'),
    K(fan_request_delete='F1007', label='Fan Request Delete'),
    K(stargram_video_create='F1008', label='Stargram Video Create'),
    K(stargram_video_update='F1009', label='Stargram Video Update'),
    K(stargram_video_delete='F1010', label='Stargram Video Delete'),
    K(profile_image_URL_delete='F1011', label='Profile Image URL Delete')
)

NOTIFICATION_TYPES = Konstants(
    K(celebrity_booking_open_details=1, label='Celebrity Booking Open Request Details'),
    K(fan_myvideos_completed_details=2, label='Fan My Videos Completed Request Details'),
    K(fan_celebrity_cancelled_details=3, label='Fan-Celebrity Cancelled Request Details'),
    K(alert_fan_celebrity_available=4, label='Alert Fan when celebrity is available'),
    K(alert_celebrity_approval=5, label='Notify Celebrity when celebrity account is approved'),
    K(request_limit_reached=6, label='Notify Celebrity when request limit has reached'),
)
