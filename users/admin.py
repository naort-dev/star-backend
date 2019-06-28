from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.contrib import admin
from django import forms
from users.models import StargramzUser, AdminUser, FanUser, CelebrityUser, Profession, GroupAccountUser, GroupAccount,\
    UserRoleMapping, Celebrity, CelebrityProfession, SettingsNotifications, FanRating, Campaign, Referral, VanityUrl, \
    CelebrityAvailableAlert, GroupType, CelebrityGroupAccount, Representative, AdminReferral, ProfileImage, \
    SocialMediaLinks, CelebrityFollow, RecentActivity
from role.models import Role
from payments.models import PaymentPayout, TipPayment
from utilities.konstants import ROLES
from utilities.utils import get_profile_images, get_profile_video, get_featured_image, get_user_role_details
from django.db.models import Q, F, Value, Case, When
from django.db.models.functions import Concat
from django.utils.safestring import mark_safe
from utilities.admin_utils import ReadOnlyModelAdmin, ReadOnlyStackedInline, ReadOnlyTabularInline
import os
from django.conf import settings


class PayoutsTabular(ReadOnlyTabularInline):
    model = PaymentPayout
    fields = ('id', 'request_name', 'status', 'fan_charged', 'starsona_company_charges',
              'fund_payed_out', 'comments', 'referral_payout')
    verbose_name_plural = 'Payouts'
    can_delete = False
    max_num = 25
    extra = 0
    min_num = 0
    readonly_fields = ('id', 'request_name', 'status', 'fan_charged', 'starsona_company_charges', 'comments',
                       'fund_payed_out', 'referral_payout')

    def request_name(self, instance):

        return mark_safe(
            '<a href="/admin/stargramz/stargramrequest/%(r)s/change">Request - %(r)s</a>'
            % {'r': str(instance.transaction.starsona.id)}
        )

    def has_add_permission(self, request):

        return False


class RoleInline(ReadOnlyStackedInline):
    model = UserRoleMapping
    fields = ('role', 'is_complete')
    max_num = 1
    verbose_name_plural = 'User role'
    can_delete = False

    def get_readonly_fields(self, request, obj=None):
        role = get_user_role_details(request.user)
        if 'role_code' in role and role['role_code'] == 'R1005':
            return self.readonly_fields
        elif 'role_code' in role and role['role_code'] == 'R1006':
            return self.readonly_fields + tuple([f.name for f in self.model._meta.fields])
        else:
            return self.readonly_fields

    def has_change_permission(self, request, obj=None):
        return True


class ReferralTabular(ReadOnlyTabularInline):
    model = Referral
    fields = ('id', 'referee', 'created_date')
    verbose_name_plural = 'Referrals'
    can_delete = True
    max_num = 25
    extra = 0
    min_num = 0
    fk_name = 'referrer'
    readonly_fields = ('id', 'referee', 'created_date',)

    def has_add_permission(self, request):

        return False


class ReferralInline(ReadOnlyStackedInline):
    model = Referral
    fields = ('referrer',)
    verbose_name_plural = 'Referred by'
    fk_name = 'referee'
    max_num = 1
    readonly_fields = ('referrer',)


class VanityUrlInline(ReadOnlyStackedInline):
    model = VanityUrl
    fields = ('name',)
    can_delete = False
    max_num = 1


class SocialMediaLinksInline(ReadOnlyStackedInline):
    model = SocialMediaLinks
    fields = ('social_link_key', 'social_link_value')
    can_delete = False
    max_num = 4


class NotificationSettingInline(ReadOnlyStackedInline):
    model = SettingsNotifications
    fields = ('celebrity_starsona_request', 'celebrity_starsona_message', 'celebrity_account_updates',
              'fan_account_updates', 'fan_starsona_messages', 'fan_starsona_videos', 'fan_email_starsona_videos',
              'mobile_number', 'mobile_country_code', 'mobile_notification', 'mobile_verified')
    max_num = 1
    verbose_name_plural = 'Notification Settings'
    can_delete = False

    def get_readonly_fields(self, request, obj=None):
        role = get_user_role_details(request.user)
        if 'role_code' in role and role['role_code'] == 'R1005':
            return self.readonly_fields
        elif 'role_code' in role and role['role_code'] == 'R1006':
            return self.readonly_fields + tuple([f.name for f in self.model._meta.fields])
        else:
            return self.readonly_fields

    def has_change_permission(self, request, obj=None):
        return True


class CelebrityForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(CelebrityForm, self).__init__(*args, **kwargs)

        self.fields['in_app_price'].required = True


class CelebrityInline(ReadOnlyStackedInline):
    model = Celebrity
    fields = ('rate', 'availability', 'admin_approval', 'star_approved', 'migrated', 'rating', 'in_app_price', 'weekly_limits', 'remaining_limit', 'follow_count',
              'featured', 'description', 'charity', 'has_fan_account',
              'check_payments', 'check_comments', 'view_count', 'trending_star_score')
    readonly_fields = ('rating', 'follow_count', 'remaining_limit', 'view_count', 'trending_star_score', 'migrated')
    max_num = 1
    verbose_name_plural = 'Celebrity Details'
    can_delete = False
    form = CelebrityForm

    def get_readonly_fields(self, request, obj=None):
        user = StargramzUser.objects.get(username=request.user)
        role = get_user_role_details(user)
        if 'role_code' in role and role['role_code'] == 'R1005':
            readonly = ('rate', 'weekly_limits',) + self.readonly_fields
            return readonly
        elif 'role_code' in role and role['role_code'] == 'R1006':
            return self.readonly_fields + tuple([f.name for f in self.model._meta.fields])
        else:
            return self.readonly_fields

    def has_change_permission(self, request, obj=None):
        return True


class RatingInline(ReadOnlyTabularInline):
    model = FanRating
    fields = ('fan_rate', 'starsona', 'fan', 'comments', 'created_date')
    readonly_fields = ('fan_rate', 'starsona', 'fan', 'comments', 'created_date')
    max_num = 10
    extra = 0
    min_num = 0
    verbose_name_plural = 'Ratings Details'
    fk_name = 'celebrity'
    can_delete = False

    def has_add_permission(self, request):

        return False


class TipPaymentAdmin(ReadOnlyTabularInline):
    model = TipPayment
    fields = ('id', 'amount', 'booking', 'fan', 'created_date')
    readonly_fields = ('id', 'amount', 'booking', 'fan', 'created_date')
    extra = 0
    min_num = 0
    verbose_name_plural = 'Tip Details'
    fk_name = 'celebrity'
    can_delete = False

    def has_add_permission(self, request):

        return False


class RepresentativeInline(ReadOnlyStackedInline):
    model = Representative
    max_num = 2
    extra = 0
    min_num = 0
    can_delete = False


class ProfessionInline(ReadOnlyStackedInline):
    model = CelebrityProfession
    fields = ('profession', )
    max_num = 3
    verbose_name_plural = 'Profession Details'
    can_delete = False

    def get_readonly_fields(self, request, obj=None):
        role = get_user_role_details(request.user)
        if 'role_code' in role and role['role_code'] == 'R1005':
            return self.readonly_fields
        elif 'role_code' in role and role['role_code'] == 'R1006':
            return self.readonly_fields + tuple([f.name for f in self.model._meta.fields])
        else:
            return self.readonly_fields

    def has_change_permission(self, request, obj=None):
        return True


class StargramzUserAdmin(UserAdmin, ReadOnlyModelAdmin):
    add_form = UserCreationForm
    list_display = ('id', 'username', 'first_name', 'last_name', 'user_types')
    list_filter = ('stargramz_user__role__name', 'is_active')

    def user_types(self, obj):
        role = UserRoleMapping.objects.get(user_id=obj.id)
        role_name = Role.objects.get(id=role.role_id).name
        return role_name

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'date_of_birth')}),
        (_('Status info'), {'fields': ('status',)}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', )}),
        (_('Important dates'), {'fields': ('last_login', 'created_date', 'modified_date', )}),
        (_('Admin referral code'), {'fields': ('admin_approval_referral_code',)})
    )
    search_fields = ('first_name', 'last_name', 'email', )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', )
        }),
    )
    ordering = ('email', )
    readonly_fields = ('created_date', 'modified_date', 'admin_approval_referral_code')
    list_per_page = 10
    inlines = [RoleInline, ReferralInline, VanityUrlInline]
    ordering = ['-id', ]


class AdminUsersAdmin(UserAdmin, ReadOnlyModelAdmin):
    name = 'myadmin'
    add_form = UserCreationForm
    list_display = ('id', 'username', 'first_name', 'last_name', 'user_types')

    def user_types(self, obj):
        role = UserRoleMapping.objects.get(user_id=obj.id)
        role_name = Role.objects.get(id=role.role_id).name
        return role_name

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'date_of_birth')}),
        (_('Status info'), {'fields': ('status',)}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', )}),
        (_('Important dates'), {'fields': ('last_login', 'created_date', 'modified_date', )})
    )
    search_fields = ('first_name', 'last_name', 'email', )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', )
        }),
    )
    ordering = ('email', )
    readonly_fields = ('created_date', 'modified_date', )
    list_per_page = 10
    inlines = [RoleInline, ]
    ordering = ['-id', ]

    def get_queryset(self, request):
        role_id = Role.objects.get(code=ROLES.admin).id
        return self.model.objects.filter(stargramz_user__role_id=role_id)


class FanUsersAdmin(UserAdmin, ReadOnlyModelAdmin):
    add_form = UserCreationForm
    list_display = ('id', 'first_name', 'last_name', 'username',)

    def user_types(self, obj):
        role = UserRoleMapping.objects.get(user_id=obj.id)
        role_name = Role.objects.get(id=role.role_id).name
        return role_name

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'date_of_birth')}),
        (_('Important dates'), {'fields': ('last_login', 'created_date', 'modified_date',)}),
        (_('Payments'), {'fields': ('stripe_customer_id', 'stripe_user_id', 'check_payments')}),
        (_('Referral Details'), {'fields': ('referral_active', 'referral_code', 'referral_campaign',
                                            'has_requested_referral', 'is_ambassador')}),
        (_('Images'), {'fields': ('profile_images',)})
    )
    search_fields = ('first_name', 'last_name', 'email',)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2',)
        }),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'nick_name', 'date_of_birth', 'order')}),
        (_('Referral Details'), {'fields': ('referral_active', 'referral_code', 'referral_campaign',
                                            'has_requested_referral', 'is_ambassador')}),
    )
    ordering = ('email',)
    readonly_fields = ('created_date', 'modified_date', 'profile_images', 'stripe_customer_id', 'stripe_user_id')
    list_per_page = 10
    inlines = [RoleInline, ReferralInline, VanityUrlInline, NotificationSettingInline]
    ordering = ['-id', ]

    def get_queryset(self, request):
        role_id = Role.objects.get(code=ROLES.fan).id
        return self.model.objects.filter(stargramz_user__role_id=role_id)

    def profile_images(self, instance):
        """
            List all the images of the user
        """
        return get_profile_images(self, instance.id, 1)

        profile_images.short_description = "Profile Images"


class CelebrityUsersAdmin(UserAdmin, ReadOnlyModelAdmin):
    add_form = UserCreationForm
    list_display = ('id', 'first_name', 'last_name', 'username', 'order', 'view_count', 'trending_star_score')
    list_filter = ('celebrity_user__admin_approval', 'temp_password', 'celebrity_user__star_approved', 'celebrity_user__created_date')

    def trending_star_score(self, obj):
        return Celebrity.objects.get(user_id=obj.id).trending_star_score

    def view_count(self, obj):
        return Celebrity.objects.get(user_id=obj.id).view_count

    def fav_count(self, obj):
        return Celebrity.objects.get(user_id=obj.id).follow_count

    def purchase_count(self, obj):
        from stargramz.models import Stargramrequest, STATUS_TYPES
        purchase_count = Stargramrequest.objects.filter(celebrity_id=obj.id).exclude(request_status=STATUS_TYPES.draft).count()
        return purchase_count

    def user_types(self, obj):
        role = UserRoleMapping.objects.get(user_id=obj.id)
        role_name = Role.objects.get(id=role.role_id).name
        return role_name

    def average_response_time(self, obj):
        return Celebrity.objects.values_list('average_response_time', flat=True).get(user_id=obj.id)

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'nick_name', 'date_of_birth', 'order', 'temp_password')}),
        (_('Referral Details'), {'fields': ('referral_active', 'referral_code', 'referral_campaign',
                                            'has_requested_referral', 'is_ambassador')}),
        (_('Ambassador'), {'fields': ('ambassador',)}),
        (_('Admin referral code'), {'fields': ('admin_approval_referral_code',)}),
        (_('Important dates'), {'fields': ('last_login', 'created_date', 'modified_date',)}),
        (_('Payments'), {'fields': ('stripe_customer_id', 'stripe_user_id', 'check_payments')}),
        (_('Images'), {'fields': ('profile_images',)}),
        (_('Featured Image'), {'fields': ('featured_image',)}),
        (_('Video'), {'fields': ('profile_video',)})
    )
    search_fields = ('first_name', 'last_name', 'nick_name', 'email',)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2',)
        }),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'nick_name', 'date_of_birth', 'order')}),
        (_('Referral Details'), {'fields': ('referral_active', 'referral_code', 'referral_campaign',
                                            'has_requested_referral', 'is_ambassador')}),
        (_('Ambassador'), {'fields': ('ambassador',)}),
    )
    ordering = ('email',)
    readonly_fields = ('created_date', 'modified_date', 'profile_images', 'profile_video',
                       'stripe_customer_id', 'featured_image', 'stripe_user_id', 'admin_approval_referral_code')
    list_per_page = 10
    inlines = [RoleInline, ReferralInline, VanityUrlInline, SocialMediaLinksInline, CelebrityInline, ProfessionInline, NotificationSettingInline, PayoutsTabular,
               RatingInline, ReferralTabular, TipPaymentAdmin, RepresentativeInline]
    inlines2 = [RoleInline, VanityUrlInline, SocialMediaLinksInline, CelebrityInline, ProfessionInline,
               NotificationSettingInline, PayoutsTabular,
               RatingInline, ReferralTabular, TipPaymentAdmin, RepresentativeInline]
    ordering = ['-id', ]

    class Media:
        js = (
            '//ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js',  # jquery
            '/media/js/profession.js',
        )

    def profile_images(self, instance):
        """
            List all the images of the user
        """
        return get_profile_images(self, instance.id, 5, avatar_id=instance.avatar_photo_id)

        profile_images.short_description = "Profile Images"

    def featured_image(self, instance):
        """
            List all the images of the user
        """
        return get_featured_image(self, instance.id, instance.featured_photo_id)

        featured_image.short_description = "Featured Images"

    def profile_video(self, instance):
        """
            Show the
        """
        return get_profile_video(instance.id)

        profile_video.short_description = "Profile Video"

    def get_queryset(self, request):
        role_id = Role.objects.get(code=ROLES.celebrity).id
        return self.model.objects.filter(Q(stargramz_user__role_id=role_id) |
                                         Q(celebrity_user__isnull=False))

    def change_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        role = get_user_role_details(request.user)
        if 'role_code' in role and role['role_code'] == 'R1005':
            extra_context['show_save_and_continue'] = True
            extra_context['show_save'] = True

        try:
            if os.environ.get('ENV') == 'dev':
                celebrity = Celebrity.objects.get(user_id=object_id)
                if celebrity.migrated:
                    extra_context['migrated'] = True
                else:
                    extra_context['show_migrate'] = True
        except:
            extra_context['show_migrate'] = True

        return super().change_view(request, object_id, extra_context=extra_context)

    def has_change_permission(self, request, obj=None):
        return True

    def get_readonly_fields(self, request, obj=None):
        role = get_user_role_details(request.user)
        if 'role_code' in role and role['role_code'] == 'R1005':
            return self.readonly_fields
        elif 'role_code' in role and role['role_code'] == 'R1006':
            return self.readonly_fields + tuple([f.name for f in self.model._meta.fields])
        else:
            return self.readonly_fields

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'ambassador':
            return AmbassadorChoiceField(queryset=StargramzUser.objects.filter(is_ambassador=True), required=False)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_inline_instances(self, request, obj=None):
        if obj and obj.ambassador:
            return [inline(self.model, self.admin_site) for inline in self.inlines2]
        return [inline(self.model, self.admin_site) for inline in self.inlines]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if '_migrate' in request.POST:
            save_data_in_production(obj)


def save_data_in_production(obj):
    """
    The function will migrate all the celebrity related data from demo to production

    :param obj:
    :return:
    """

    from config.models import Config
    from .tasks import change_file_bucket, send_star_approval_mail
    import uuid

    production_host = Config.objects.get(key='production_db_host').value
    settings.DATABASES.get('production').update({'HOST': production_host})
    using = 'production'
    reset_id = uuid.uuid4()

    # Creating a user in production db

    user, created = StargramzUser.objects.using(using).get_or_create(username=obj.email, email=obj.email)

    user.nick_name=obj.nick_name
    user.first_name=obj.first_name
    user.last_name=obj.last_name
    user.reset_id = reset_id
    user.referral_code = obj.referral_code
    user.temp_password = obj.temp_password
    user.is_ambassador = obj.is_ambassador
    user.stripe_customer_id = obj.stripe_customer_id
    user.profile_photo = obj.profile_photo
    user.save()

    obj.reset_id = reset_id
    obj.save()

    # Creating an object in admin referral in production db

    if obj.admin_approval_referral_code:
        referral, activate = AdminReferral.objects.using(using).get_or_create(
            referral_code=obj.admin_approval_referral_code.referral_code,
            activate=obj.admin_approval_referral_code.activate
        )
        user.admin_approval_referral_code = referral
        user.save()

    # Creating the user role mapping same as the current db into production db

    try:
        mapping = UserRoleMapping.objects.get(user_id=obj.id)
        role = Role.objects.using(using).get(code=mapping.role.code)
        UserRoleMapping.objects.using(using).get_or_create(
                user_id=user.id,
                role=role,
                is_complete=mapping.is_complete
            )
    except Exception as e:
        print(str(e))

    # Creating the Referral entry into production db

    try:
        refers = Referral.objects.filter(referrer_id=obj.id)
        for refer in refers:
            try:
                refere = StargramzUser.objects.using(using).get(email=refer.referee.email)
                Referral.objects.using(using).get_or_create(referrer_id=user.id, referee_id=refere.id)
            except:
                pass
        refers = Referral.objects.get(referee_id=obj.id)
        referer = StargramzUser.objects.using(using).get(email=refer.referrer.email)
        Referral.objects.using(using).get_or_create(referrer_id=referer.id, referee_id=user.id)
    except Exception as e:
        print(str(e))

    # Creating the vanity url into production db

    try:
        vanity = VanityUrl.objects.get(user_id=obj.id)
        VanityUrl.objects.using(using).get_or_create(name=vanity.name, user_id=user.id)
    except Exception as e:
        print(str(e))

    # Creating the setting notification into production db

    try:
        settingss = SettingsNotifications.objects.get(user_id=obj.id)
        SettingsNotifications.objects.using(using).get_or_create(
            user_id=user.id,
            celebrity_starsona_request=settingss.celebrity_starsona_request,
            celebrity_starsona_message=settingss.celebrity_starsona_message,
            celebrity_account_updates=settingss.celebrity_account_updates,
            fan_account_updates=settingss.fan_account_updates,
            fan_starsona_messages=settingss.fan_starsona_messages,
            fan_starsona_videos=settingss.fan_starsona_videos,
            fan_email_starsona_videos=settingss.fan_email_starsona_videos,
            email_notification=settingss.email_notification,
            secondary_email=settingss.secondary_email,
            mobile_country_code=settingss.mobile_country_code,
            mobile_number=settingss.mobile_number,
            mobile_notification=settingss.mobile_notification,
            mobile_verified=settingss.mobile_verified,
            verification_uuid=settingss.verification_uuid
            )
    except Exception as e:
        print(str(e))

    # Creating the profile image table entry in production db
    # Need to upload the file which is downloaded from staging s3 bucket

    try:
        images = ProfileImage.objects.filter(user_id=obj.id)
        for image in images:
            profile_image_production, created = ProfileImage.objects.using(using).get_or_create(
                user_id=user.id,
                photo=image.photo,
                status=image.status,
                thumbnail=image.thumbnail,
                medium_thumbnail=image.medium_thumbnail
            )
            profile_images = Config.objects.get(key='profile_images').value

            # Moving the profile image and the thumbnail from demo to production

            change_file_bucket.delay(profile_images, image.photo)
            change_file_bucket.delay(profile_images, image.thumbnail)

            if obj.avatar_photo and obj.avatar_photo.id == image.id:
                user.avatar_photo = profile_image_production
            if obj.featured_photo and obj.featured_photo.id == image.id:
                user.featured_photo = profile_image_production
            user.save()
    except Exception as e:
        print(str(e))

    # Creating data into Celebrity table

    try:
        celebrity = Celebrity.objects.get(user_id=obj.id)
        Celebrity.objects.using(using).get_or_create(
            user_id=user.id,
            rate = celebrity.rate,
            in_app_price=celebrity.in_app_price,
            rating=celebrity.rating,
            weekly_limits=celebrity.weekly_limits,
            profile_video=celebrity.profile_video,
            follow_count=celebrity.follow_count,
            description=celebrity.description,
            charity=celebrity.charity,
            availability=celebrity.availability,
            admin_approval=celebrity.admin_approval,
            featured=celebrity.featured,
            remaining_limit=celebrity.remaining_limit,
            view_count=celebrity.view_count,
            stripe_user_id=celebrity.stripe_user_id,
            check_comments=celebrity.check_comments,
            check_payments=celebrity.check_payments,
            has_fan_account=celebrity.has_fan_account,
            trending_star_score=celebrity.trending_star_score,
            average_response_time=celebrity.average_response_time,
            star_approved=False
        )
        profile_video = Config.objects.get(key='authentication_videos').value

        # Moving the profile video from demo to production

        change_file_bucket.delay(profile_video, celebrity.profile_video)
        celebrity.migrated = True
        celebrity.save()
    except Exception as e:
        print(str(e))

    # Creating CelebrityProfession relation into production db

    try:
        professions = CelebrityProfession.objects.filter(user_id=obj.id)
        for profession in professions:
            if profession.profession.parent:
                profession_class = Profession.objects.using(using).filter(parent__title=profession.profession.parent.title)
            else:
                profession_class = Profession.objects.using(using).filter(parent=None)
            profession_new = profession_class.get(title=profession.profession.title)
            CelebrityProfession.objects.using(using).get_or_create(
                user_id=user.id,
                profession=profession_new
            )
    except Exception as e:
        print(str(e))

    # Sending e-mail to the celebrity informing about the migration into production

    send_star_approval_mail.delay(obj.id)


class AmbassadorChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return "{}".format(obj.username)


class ProfessionAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'title', 'description', 'parent', 'order')
    search_fields = ('title',)
    ordering = ('title',)
    list_per_page = 10
    ordering = ['order', ]

    def get_fieldsets(self, request, obj=None):
        fields = ('title', 'description', 'parent', 'file')
        fields = fields + ('order',) if not obj else fields
        if obj and not obj.parent:
            fields = fields + ('order',)
        fieldsets = (
            (None, {'fields': fields}),
        )
        return fieldsets


class RatingAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'fan_rate', 'starsona', 'celebrity')
    search_fields = ('celebrity__username', 'starsona__id')
    list_per_page = 10
    ordering = ('id',)
    ordering = ['id', ]


class CampaignAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'title', 'discount', 'created_date')

    list_per_page = 10
    ordering = ['-id', ]

    def get_fieldsets(self, request, obj=None):
        fields = ('title', 'description', 'valid_from', 'valid_till', 'discount', 'max_referral_amount',
                  'valid_for_days', 'enable_two_way', 'request_for_user',)
        fieldsets = (
            ('Campaigns', {'fields': fields}),
        )
        return fieldsets


class CelebrityAvailabilityAlertAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'celebrity', 'fan', 'notification_send', 'created_date')

    list_per_page = 10

    class Media:
        js = (
            '//ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js',  # jquery
            '/media/js/alert_fan.js',
        )


class GroupAccountInline(ReadOnlyStackedInline):
    model = GroupAccount
    readonly_fields = ('follow_count',)
    fieldsets = (
        (_('Group info'), {'fields': ('group_type', 'description', 'tags', 'website', 'phone',)}),
        (_('Address'), {'fields': ('address', 'address_2', 'city', 'state', 'zip', 'country',)}),
        (_('Important'), {'fields': ('admin_approval', 'follow_count',)}),
    )
    max_num = 1
    verbose_name_plural = 'Group Account Details'
    can_delete = False


class CelebrityGroupAccountTabular(ReadOnlyTabularInline):
    model = CelebrityGroupAccount
    fields = ('user', 'account', 'approved', 'celebrity_invite', 'order', 'created_date', 'modified_date')
    verbose_name_plural = 'Celebrity users'
    extra = 0
    min_num = 0
    fk_name = 'account'
    readonly_fields = ('user', 'account', 'celebrity_invite', 'order', 'created_date', 'modified_date')

    def has_add_permission(self, request):

        return False


class CelebrityDisplayOrganizerForm(forms.ModelForm):
    class Meta:
        model = GroupAccountUser
        fields = '__all__'

    def clean(self):
        if 'first_name' in self.cleaned_data:
            try:
                user = StargramzUser.objects.filter(first_name=str(self.cleaned_data['first_name']))[0]
            except:
                pass
            else:
                if str(user.username) == str(self.cleaned_data['username']):
                    pass
                else:
                    raise forms.ValidationError(
                        "Error: Group name must be unique %s already exist" % self.cleaned_data['first_name'])
        return self.cleaned_data


class GroupAccountUsersAdmin(UserAdmin, ReadOnlyModelAdmin):
    add_form = UserCreationForm
    form = CelebrityDisplayOrganizerForm
    list_display = ('id', 'first_name', 'last_name', 'username', 'order')
    list_filter = ('group_account__admin_approval',)

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'nick_name', 'phone', 'date_of_birth',
                                         'show_nick_name', 'order')}),
        (_('Referral Details'), {'fields': ('referral_active', 'referral_code', 'referral_campaign',
                                            'has_requested_referral')}),
        (_('Payments'), {'fields': ('stripe_customer_id', 'stripe_user_id', 'check_payments')}),
        (_('Important dates'), {'fields': ('last_login', 'created_date', 'modified_date',)}),
        (_('Images'), {'fields': ('profile_images',)}),
        (_('Featured Image'), {'fields': ('featured_image',)}),
    )
    search_fields = ('first_name', 'last_name', 'nick_name', 'email',)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2',)
        }),
    )
    ordering = ('email',)
    readonly_fields = ('created_date', 'modified_date', 'profile_images', 'featured_image', 'stripe_customer_id',
                       'stripe_user_id')
    list_per_page = 10
    inlines = [GroupAccountInline, ReferralInline, VanityUrlInline, RoleInline, CelebrityGroupAccountTabular]
    ordering = ['-id', ]

    def get_queryset(self, request):
        role_id = Role.objects.get(code=ROLES.group_account).id
        return self.model.objects.filter(Q(stargramz_user__role_id=role_id) |
                                         Q(group_account__isnull=False))

    def profile_images(self, instance):
        """
            List all the images of the user
        """
        return get_profile_images(self, instance.id, 5, avatar_id=instance.avatar_photo_id)

        profile_images.short_description = "Profile Images"

    def featured_image(self, instance):
        """
            List all the images of the user
        """
        return get_featured_image(self, instance.id, instance.featured_photo_id)

        featured_image.short_description = "Featured Images"


class JoinGroupAdmin(ReadOnlyModelAdmin):
    list_display = ('celebrity_name', 'group_name', 'approved', 'celebrity_invite', 'order', 'created_date',
                    'modified_date')
    readonly_fields = ('order', 'created_date', 'modified_date')

    def celebrity_name(self, obj):
        return obj.user.get_short_name()

    def group_name(self, obj):
        return obj.account.get_short_name()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'user':
            query_set = StargramzUser.objects.filter(celebrity_user__admin_approval=True)
            query_set = query_set.annotate(sort_name=Case(
                When(Q(nick_name__isnull=False) & ~Q(nick_name=''), then=F('nick_name')),
                default=Concat('first_name', Value(' '), 'last_name')))
            return UserChoiceField(queryset=query_set.order_by('sort_name').distinct(), required=False)
        if db_field.name == 'account':
            query_set = StargramzUser.objects.filter(group_account__admin_approval=True)
            query_set = query_set.annotate(sort_name=Case(
                When(Q(nick_name__isnull=False) & ~Q(nick_name=''), then=F('nick_name')),
                default=Concat('first_name', Value(' '), 'last_name')))
            return UserChoiceField(queryset=query_set.order_by('sort_name').distinct(), required=False)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class UserChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return "{}".format(obj.get_short_name())


class GroupTypeAdmin(ReadOnlyModelAdmin):
    model = GroupType
    list_display = ('id', 'group_name', 'order', 'created_date', 'order')


class ReferralAdmin(ReadOnlyModelAdmin):
    model = Referral
    list_display = ('id', 'referee_name', 'referrer_name', 'created_date', 'source')
    fieldsets = (
        (_('Referral Details'), {'fields': ('referee', 'referee_name', 'referrer', 'referrer_name', 'source')}),
        (_('Important dates'), {'fields': ('created_date',)}),
    )

    readonly_fields = ('created_date', 'referrer_name', 'referee_name')

    def referee_name(self, obj):
        return obj.referee.get_short_name()

    def referrer_name(self, obj):
        return obj.referrer.get_short_name()


class AdminReferralAdmin(ReadOnlyModelAdmin):
    model = AdminReferral
    list_display = ('id', 'referral_code', 'activate', 'created_date')


class CelebrityFollowAdmin(ReadOnlyModelAdmin):
    model = CelebrityFollow
    list_display = ('id', 'celebrity', 'fan', 'is_group', 'created_date')
    search_fields = ('celebrity__email',)


class RecentActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'activity_from_user', 'activity_to_user', 'request', 'activity_type', 'created_date')


admin.site.register(GroupType, GroupTypeAdmin)
admin.site.register(Profession, ProfessionAdmin)
admin.site.register(StargramzUser, StargramzUserAdmin)
admin.site.register(AdminUser, AdminUsersAdmin)
admin.site.register(FanUser, FanUsersAdmin)
admin.site.register(CelebrityUser, CelebrityUsersAdmin)
admin.site.register(GroupAccountUser, GroupAccountUsersAdmin)
admin.site.register(FanRating, RatingAdmin)
admin.site.register(Campaign, CampaignAdmin)
admin.site.register(Referral, ReferralAdmin)
admin.site.register(CelebrityGroupAccount, JoinGroupAdmin)
admin.site.register(CelebrityAvailableAlert, CelebrityAvailabilityAlertAdmin)
admin.site.register(AdminReferral, AdminReferralAdmin)
admin.site.register(CelebrityFollow, CelebrityFollowAdmin)
admin.site.register(RecentActivity, RecentActivityAdmin)
