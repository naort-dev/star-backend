from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.contrib import admin
from users.models import StargramzUser, AdminUser, FanUser, CelebrityUser, Profession, \
    UserRoleMapping, Celebrity, CelebrityProfession, SettingsNotifications, FanRating
from role.models import Role
from payments.models import PaymentPayout
from utilities.konstants import ROLES
from utilities.utils import get_profile_images, get_profile_video
from django.db.models import Q
from django.utils.safestring import mark_safe


class PayoutsTabular(admin.TabularInline):
    model = PaymentPayout
    fields = ('id', 'request_name', 'status', 'fan_charged', 'starsona_company_charges',
              'fund_payed_out', 'comments')
    verbose_name_plural = 'Payouts'
    can_delete = False
    max_num = 25
    extra = 0
    min_num = 0
    readonly_fields = ('id', 'request_name', 'fan_charged', 'starsona_company_charges', 'fund_payed_out')

    def request_name(self, instance):

        return mark_safe(
            '<a href="/admin/stargramz/stargramrequest/%(r)s/change">Request - %(r)s</a>'
            % {'r': str(instance.transaction.starsona.id)}
        )

    def has_add_permission(self, request):

        return False


class RoleInline(admin.StackedInline):
    model = UserRoleMapping
    fields = ('role', 'is_complete')
    max_num = 1
    verbose_name_plural = 'User role'
    can_delete = False


class NotificationSettingInline(admin.StackedInline):
    model = SettingsNotifications
    fields = ('celebrity_starsona_request', 'celebrity_starsona_message', 'celebrity_account_updates',
              'fan_account_updates', 'fan_starsona_messages', 'fan_starsona_videos', 'fan_email_starsona_videos')
    max_num = 1
    verbose_name_plural = 'Notification Settings'
    can_delete = False


class CelebrityInline(admin.StackedInline):
    model = Celebrity
    fields = ('rate', 'availability', 'admin_approval', 'rating', 'weekly_limits', 'remaining_limit', 'follow_count', 'stripe_user_id',
              'featured', 'description', 'charity', 'has_fan_account', 'check_payments', 'check_comments')
    readonly_fields = ('rating', 'follow_count', 'stripe_user_id', 'remaining_limit')
    max_num = 1
    verbose_name_plural = 'Celebrity Details'
    can_delete = False


class RatingInline(admin.TabularInline):
    model = FanRating
    fields = ('fan_rate', 'starsona', 'fan', 'created_date')
    readonly_fields = ('fan_rate', 'starsona', 'fan', 'created_date')
    max_num = 10
    extra = 0
    min_num = 0
    verbose_name_plural = 'Ratings Details'
    fk_name = 'celebrity'
    can_delete = False

    def has_add_permission(self, request):

        return False


class ProfessionInline(admin.StackedInline):
    model = CelebrityProfession
    fields = ('profession', )
    max_num = 3
    verbose_name_plural = 'Profession Details'
    can_delete = False


class StargramzUserAdmin(UserAdmin):
    add_form = UserCreationForm
    list_display = ('id', 'username', 'first_name', 'last_name', 'user_types')

    def user_types(self, obj):
        role = UserRoleMapping.objects.get(user_id=obj.id)
        role_name = Role.objects.get(id=role.role_id).name
        return role_name

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone', 'date_of_birth')}),
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


class AdminUsersAdmin(UserAdmin):
    name = 'myadmin'
    add_form = UserCreationForm
    list_display = ('id', 'username', 'first_name', 'last_name', 'user_types')

    def user_types(self, obj):
        role = UserRoleMapping.objects.get(user_id=obj.id)
        role_name = Role.objects.get(id=role.role_id).name
        return role_name

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone', 'date_of_birth')}),
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


class FanUsersAdmin(UserAdmin):
    add_form = UserCreationForm
    list_display = ('id', 'first_name', 'last_name', 'username',)

    def user_types(self, obj):
        role = UserRoleMapping.objects.get(user_id=obj.id)
        role_name = Role.objects.get(id=role.role_id).name
        return role_name

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone', 'date_of_birth')}),
        (_('Important dates'), {'fields': ('last_login', 'created_date', 'modified_date',)}),
        (_('Payments'), {'fields': ('stripe_customer_id',)}),
        (_('Images'), {'fields': ('profile_images',)})
    )
    search_fields = ('first_name', 'last_name', 'email',)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2',)
        }),
    )
    ordering = ('email',)
    readonly_fields = ('created_date', 'modified_date', 'profile_images', 'stripe_customer_id')
    list_per_page = 10
    inlines = [RoleInline, NotificationSettingInline]
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


class CelebrityUsersAdmin(UserAdmin):
    add_form = UserCreationForm
    list_display = ('id', 'first_name', 'last_name', 'username', 'order')
    list_filter = ('celebrity_user__admin_approval', 'stargramz_user__is_complete')

    def user_types(self, obj):
        role = UserRoleMapping.objects.get(user_id=obj.id)
        role_name = Role.objects.get(id=role.role_id).name
        return role_name

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'nick_name', 'phone', 'date_of_birth',
                                         'show_nick_name', 'order')}),
        (_('Important dates'), {'fields': ('last_login', 'created_date', 'modified_date',)}),
        (_('Payments'), {'fields': ('stripe_customer_id',)}),
        (_('Images'), {'fields': ('profile_images',)}),
        (_('Video'), {'fields': ('profile_video',)})
    )
    search_fields = ('first_name', 'last_name', 'nick_name', 'email',)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2',)
        }),
    )
    ordering = ('email',)
    readonly_fields = ('created_date', 'modified_date', 'profile_images', 'profile_video', 'stripe_customer_id')
    list_per_page = 10
    inlines = [RoleInline, CelebrityInline, ProfessionInline, NotificationSettingInline, PayoutsTabular, RatingInline]
    ordering = ['-id', ]

    def profile_images(self, instance):
        """
            List all the images of the user
        """
        return get_profile_images(self, instance.id, 5, avatar_id=instance.avatar_photo_id)

        profile_images.short_description = "Profile Images"

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


class ProfessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'parent', 'order')
    search_fields = ('title',)
    ordering = ('title',)
    list_per_page = 10
    ordering = ['order', ]

    def get_fieldsets(self, request, obj=None):
        fields = ('title', 'parent', 'file')
        fields = fields + ('order',) if not obj else fields
        if obj and not obj.parent:
            fields = fields + ('order',)
        fieldsets = (
            (None, {'fields': fields}),
        )
        return fieldsets


class RatingAdmin(admin.ModelAdmin):
    list_display = ('id', 'fan_rate', 'celebrity', 'fan')
    list_per_page = 10
    ordering = ('id',)
    ordering = ['id', ]


admin.site.register(Profession, ProfessionAdmin)
admin.site.register(StargramzUser, StargramzUserAdmin)
admin.site.register(AdminUser, AdminUsersAdmin)
admin.site.register(FanUser, FanUsersAdmin)
admin.site.register(CelebrityUser, CelebrityUsersAdmin)
admin.site.register(FanRating, RatingAdmin)
