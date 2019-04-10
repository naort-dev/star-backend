from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.contrib import admin
from django import forms
from users.models import StargramzUser, AdminUser, FanUser, CelebrityUser, Profession, GroupAccountUser, GroupAccount,\
    UserRoleMapping, Celebrity, CelebrityProfession, SettingsNotifications, FanRating, Campaign, Referral, VanityUrl, \
    CelebrityAvailableAlert, GroupType, CelebrityGroupAccount, Representative, AdminReferral
from role.models import Role
from payments.models import PaymentPayout, TipPayment
from utilities.konstants import ROLES
from utilities.utils import get_profile_images, get_profile_video, get_featured_image, get_user_role_details
from django.db.models import Q
from django.utils.safestring import mark_safe
from utilities.admin_utils import ReadOnlyModelAdmin, ReadOnlyStackedInline, ReadOnlyTabularInline


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


class CelebrityInline(ReadOnlyStackedInline):
    model = Celebrity
    fields = ('rate', 'availability', 'admin_approval', 'rating', 'in_app_price', 'weekly_limits', 'remaining_limit', 'follow_count',
              'featured', 'description', 'charity', 'has_fan_account',
              'check_payments', 'check_comments', 'view_count', 'trending_star_score')
    readonly_fields = ('rating', 'follow_count', 'remaining_limit', 'view_count', 'trending_star_score')
    max_num = 1
    verbose_name_plural = 'Celebrity Details'
    can_delete = False

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
    list_filter = ('stargramz_user__role__name',)

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
    list_display = ('id', 'first_name', 'last_name', 'username', 'order')
    list_filter = ('celebrity_user__admin_approval', 'stargramz_user__is_complete')

    def user_types(self, obj):
        role = UserRoleMapping.objects.get(user_id=obj.id)
        role_name = Role.objects.get(id=role.role_id).name
        return role_name

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'nick_name', 'date_of_birth', 'order')}),
        (_('Referral Details'), {'fields': ('referral_active', 'referral_code', 'referral_campaign',
                                            'has_requested_referral', 'is_ambassador')}),
        (_('Ambassador'), {'fields': ('ambassador',)}),
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
                       'stripe_customer_id', 'featured_image', 'stripe_user_id')
    list_per_page = 10
    inlines = [RoleInline, ReferralInline, VanityUrlInline, CelebrityInline, ProfessionInline, NotificationSettingInline, PayoutsTabular,
               RatingInline, ReferralTabular, TipPaymentAdmin, RepresentativeInline]
    inlines2 = [RoleInline, VanityUrlInline, CelebrityInline, ProfessionInline,
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


class GroupAccountUsersAdmin(UserAdmin, ReadOnlyModelAdmin):
    add_form = UserCreationForm
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
    list_display = ('user', 'account', 'approved', 'celebrity_invite', 'order', 'created_date', 'modified_date')
    readonly_fields = ('order', 'created_date', 'modified_date')


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
