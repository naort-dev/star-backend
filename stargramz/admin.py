from django.utils.translation import ugettext_lazy as _
from django.contrib import admin
from .models import Occasion, Stargramrequest, StargramVideo, OccasionRelationship, ReportAbuse, OrderRelationship,\
    Comment, Reaction, BookingAdminAdd, ReactionAbuse
from payments.models import StarsonaTransaction, TipPayment
from config.models import Config
from django.utils.safestring import mark_safe
from utilities.utils import get_pre_signed_get_url, get_audio, get_s3_public_url
from utilities.admin_utils import ReadOnlyModelAdmin, ReadOnlyStackedInline, ReadOnlyTabularInline
import json


class AbuseInline(ReadOnlyStackedInline):
    model = ReportAbuse
    fields = ('request', 'comments', 'reported_by', 'read_flag')
    min_num = 0
    max_num = 10
    extra = 0
    verbose_name_plural = 'Abuse Details'
    can_delete = False
    readonly_fields = ('request', 'comments')

    def has_add_permission(self, request):

        return False


class TransactionsInline(ReadOnlyStackedInline):
    model = StarsonaTransaction
    fields = ('starsona', 'order_id', 'fan', 'celebrity', 'transaction_status', 'source_id',
              'stripe_transaction_id', 'stripe_refund_id', 'amount', 'comments', 'created_date', 'modified_date')

    min_num = 0
    max_num = 10
    extra = 0
    verbose_name_plural = 'Transaction Details'
    can_delete = True
    readonly_fields = ('order_id', 'fan', 'celebrity', 'transaction_status', 'source_id', 'stripe_transaction_id',
                       'stripe_refund_id', 'amount', 'comments', 'created_date', 'modified_date')

    def has_add_permission(self, request):
        return False

    def order_id(self, instance):
        return instance.order_id()


class StargramVideosInline(ReadOnlyStackedInline):
    model = StargramVideo
    fields = ('stragramz_request', 'video_thumbnail', 'video_link', 'video',
              'duration', 'created_date')
    readonly_fields = ('created_date', 'video_thumbnail', 'video_link', 'status')
    min_num = 0
    max_num = 5
    extra = 0
    verbose_name_plural = 'Video Details'
    can_delete = True

    def has_add_permission(self, request):
        return False

    def video_thumbnail(self, instance):
        """
            Embed the video thumbnail image
        """
        config = Config.objects.get(key='stargram_video_thumb')

        if instance.thumbnail:
            return mark_safe('<img src="%s" class="img-thumbnail" width="200" height="200"/>'
                             % get_pre_signed_get_url(instance.thumbnail, config.value))
        else:
            return mark_safe('<span>No Video image available.</span>')

    def video_link(self, instance):
        """
            Embed the video from S3
        """
        config = Config.objects.get(key='stargram_videos')

        if instance.video:
            return mark_safe('<video width="320" height="240" controls><source src="%s" type="video/mp4">'
                             'Your browser does not support the video tag.</video>'
                             % get_pre_signed_get_url(instance.video, config.value))
        else:
            return mark_safe('<span>No Video available.</span>')


class StargramVideosAdminInline(ReadOnlyStackedInline):
    model = StargramVideo
    fields = ('stragramz_request', 'video_thumbnail', 'video_link', 'video', 'status',
              'duration', 'created_date')
    readonly_fields = ('created_date', 'video_link', 'video_thumbnail')
    min_num = 1
    max_num = 3
    extra = 0
    verbose_name_plural = 'Video Details'
    can_delete = True

    def video_thumbnail(self, instance):
        """
            Embed the video thumbnail image
        """
        config = Config.objects.get(key='stargram_video_thumb')

        if instance.thumbnail:
            return mark_safe('<img src="%s" class="img-thumbnail" width="200" height="200"/>'
                             % get_pre_signed_get_url(instance.thumbnail, config.value))
        else:
            return mark_safe('<span>No Video image available.</span>')

    def video_link(self, instance):
        """
            Embed the video from S3
        """
        config = Config.objects.get(key='stargram_videos')

        if instance.video:
            return mark_safe('<video width="320" height="240" controls><source src="%s" type="video/mp4">'
                             'Your browser does not support the video tag.</video>'
                             % get_pre_signed_get_url(instance.video, config.value))
        else:
            return mark_safe('<span>No Video available.</span>')


class TransactionsAdminInline(ReadOnlyStackedInline):
    model = StarsonaTransaction
    fields = ('starsona', 'fan', 'celebrity', 'transaction_status', 'source_id',
              'stripe_transaction_id', 'stripe_refund_id', 'amount', 'comments')

    min_num = 1
    max_num = 1
    extra = 0
    verbose_name_plural = 'Transaction Details'
    can_delete = True


class OrderRelationshipInline(ReadOnlyTabularInline):
    model = OrderRelationship
    extra = 1
    can_delete = True

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "relation":
            kwargs["queryset"] = OccasionRelationship.objects.filter(status=True).distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ReactionStackedInline(ReadOnlyStackedInline):
    model = Reaction
    min_num = 0
    max_num = 3
    extra = 0
    fields = ('file_type', 'reaction_file', 'file_link')
    readonly_fields = ('file_link', )
    search_fields = ('booking', 'user',)

    def has_add_permission(self, request):
        return False

    def file_link(self, instance):
        """
            Embed the video from S3
        """
        config = Config.objects.get(key='reaction_files')

        if instance.file_type == 2:
            return mark_safe('<video width="320" height="240" controls><source src="%s" type="video/mp4">'
                             'Your browser does not support the video tag.</video>'
                             % get_s3_public_url(instance.reaction_file, config.value))
        elif instance.file_type == 1:
            return mark_safe('<image width="320" height="240" src="%s"/>'
                             % get_s3_public_url(instance.reaction_file, config.value))
        else:
            return mark_safe('<span>No File available.</span>')

class OcccassionRelationshipAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'title', 'status')

    fieldsets = (
        (_('Basic info'), {'fields': ('title', 'status')}),
    )
    ordering = ('id',)


class AbuseAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'request_url', 'reported_by', 'read_flag')
    fieldsets = (
        (_('Basic info'), {'fields': ('request', 'comments', 'reported_by', 'read_flag')}),
    )
    verbose_name_plural = 'Abuse Details'

    def request_url(self, instance):
        return "<a href='/admin/stargramz/stargramrequest/%d/change'>%s</a>" % (instance.request_id, instance.request)

    request_url.allow_tags = True
    request_url.short_description = 'Request'


class ReactionAbuseAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'reaction', 'reported_by', 'read_flag')
    fieldsets = (
        (_('Basic info'), {'fields': ('reaction', 'comments', 'reported_by', 'read_flag')}),
    )
    verbose_name_plural = 'Reaction Abuse Details'


class OccasionAdmin(ReadOnlyModelAdmin):
    # form = CategoriesForm
    list_display = ('id', 'title')

    fieldsets = (
        (_('Basic info'), {'fields': ('title', 'type', 'other_check', 'request_type', 'visibility')}),
    )
    search_fields = ('title',)

    inlines = (OrderRelationshipInline,)


class TipPaymentAdmin(ReadOnlyTabularInline):
    model = TipPayment
    fields = ('id', 'amount', 'booking', 'fan', 'celebrity', 'created_date')
    readonly_fields = ('id', 'amount', 'booking', 'fan', 'celebrity', 'created_date')
    extra = 0
    min_num = 0
    verbose_name_plural = 'Tip Details'
    fk_name = 'booking'
    can_delete = False

    def has_add_permission(self, request):

        return False


class StargramrequestAdmin(ReadOnlyModelAdmin):

    actions = ['make_complete']
    list_display = ('id', 'fan', 'celebrity', 'occasion', 'request_status',)
    list_filter = ('request_status', 'request_type')
    fieldsets = (
        (_('Basic info'), {'fields': ('booking_title', 'fan', 'celebrity', 'occasion', 'request_data', 'request_type')}),
        (_('Audios'), {'fields': ('booking_from_audio', 'booking_to_audio',)}),
        (_('Info'), {'fields': ('share_check', 'request_status', 'public_request', 'priorty',)}),
        (_('Cancellation reason'), {'fields': ('comment',)}),
        (_('Dates'), {'fields': ('created_date', 'modified_date')}),
    )
    readonly_fields = ('due_date', 'request_data', 'booking_from_audio', 'comment',
                       'booking_to_audio', 'created_date', 'modified_date',)
    search_fields = ('celebrity__username', 'fan__username', 'occasion__title', 'request_status')
    inlines = [StargramVideosInline, TransactionsInline, AbuseInline, ReactionStackedInline, TipPaymentAdmin]

    def make_complete(self, request, queryset):
        queryset.update(request_status=6)
    make_complete.short_description = "Mark selected Bookings as Completed"

    def booking_from_audio(self, instance):

        return get_audio(instance.from_audio_file)

    def booking_to_audio(self, instance):

        return get_audio(instance.to_audio_file)

    def request_data(self, instance):
        data = json.loads(instance.request_details)
        string = ''
        for attribute, value in sorted(data.items()):
            try:
                for attributes, values in value.items():
                    string += "<tr><td>%s - %s</td><td>%s</td></tr>" % (
                        attribute.capitalize(),
                        attributes.capitalize(),
                        str(values)
                    )
            except Exception:
                if value:
                    string += "<tr><td>%s</td><td>%s</td></tr>" % (attribute.capitalize(), str(value))

        return mark_safe("<table width='500px'>%s</table>" % string)


class StargramVideosAdmin(ReadOnlyModelAdmin):

    list_display = ('id', 'stragramz_request', 'video_duration', 'status', 'created_date')

    fieldsets = (
        (_('Stargramz info'), {'fields': ('stragramz_request', 'video_thumbnail', 'video_link', 'video', 'read_status')}),
        (_('Video info'), {'fields': ('duration', 'created_date',)}),
    )
    readonly_fields = ('created_date', 'video_thumbnail', 'video_link', 'status')
    search_fields = ('stragramz_request__booking_title', 'video')

    def video_duration(self, obj):
        if obj.duration:
            return obj.duration.strftime("%H:%M:%S")
        else:
            return '00:00:00'

    def video_thumbnail(self, instance):
        """
            Embed the video thumbnail image
        """
        config = Config.objects.get(key='stargram_video_thumb')

        if instance.thumbnail:
            return mark_safe('<img src="%s" class="img-thumbnail" width="200" height="200"/>'
                             % get_pre_signed_get_url(instance.thumbnail, config.value))
        else:
            return mark_safe('<span>No Video image available.</span>')

    def video_link(self, instance):
        """
            Embed the video from S3
        """
        config = Config.objects.get(key='stargram_videos')

        if instance.video:
            return mark_safe('<video width="320" height="240" controls><source src="%s" type="video/mp4">'
                             'Your browser does not support the video tag.</video>'
                             % get_pre_signed_get_url(instance.video, config.value))
        else:
            return mark_safe('<span>No Video available.</span>')


class CommentsAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'video', 'user', 'created_date')

    fieldsets = (
        (_('Comment info'), {'fields': ('video', 'comments', 'user', 'created_date',)}),
    )
    readonly_fields = ('created_date',)
    search_fields = ('comments',)


class ReactionsAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'booking', 'user', 'created_date')

    fieldsets = (
        (_('Reaction info'), {'fields': ('booking', 'file_type', 'reaction_file', 'file_link', 'user', 'created_date',)}),
    )
    readonly_fields = ('file_link', 'created_date',)
    search_fields = ('booking', 'user',)

    def file_link(self, instance):
        """
            Embed the video from S3
        """
        config = Config.objects.get(key='reaction_files')

        if instance.file_type == 2:
            return mark_safe('<video width="320" height="240" controls><source src="%s" type="video/mp4">'
                             'Your browser does not support the video tag.</video>'
                             % get_s3_public_url(instance.reaction_file, config.value))
        elif instance.file_type == 1:
            return mark_safe('<image width="320" height="240" src="%s"/>'
                             % get_s3_public_url(instance.reaction_file, config.value))
        else:
            return mark_safe('<span>No File available.</span>')


class BookingsAddOnlyAdmin(ReadOnlyModelAdmin):

    list_display = ('id', 'fan', 'celebrity', 'occasion', 'request_status',)
    list_filter = ('request_status', 'request_type')
    fieldsets = (
        (_('Complete Booking'), {'fields': ('complete_booking',)}),
        (_('Basic info'), {'fields': ('booking_title', 'fan', 'celebrity', 'occasion', 'request_data', 'request_type')}),
        (_('Audios'), {'fields': ('booking_from_audio', 'booking_to_audio',)}),
        (_('Info'), {'fields': ('share_check', 'request_status', 'public_request', 'priorty',)}),
        (_('Cancellation reason'), {'fields': ('comment',)}),
        (_('Dates'), {'fields': ('created_date', 'modified_date')}),
    )
    readonly_fields = ('due_date', 'request_data', 'booking_from_audio', 'complete_booking',
                       'booking_to_audio', 'created_date', 'modified_date',)
    inlines = [StargramVideosAdminInline, TransactionsAdminInline]

    class Media:
        js = (
            '//ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js',  # jquery
            '/media/js/admin-booking.js',
        )

    def make_complete(self, request, queryset):
        queryset.update(request_status=6)
    make_complete.short_description = "Mark selected Bookings as Completed"

    def booking_from_audio(self, instance):

        return get_audio(instance.from_audio_file)

    def booking_to_audio(self, instance):

        return get_audio(instance.to_audio_file)

    def request_data(self, instance):
        data = json.loads(instance.request_details)
        string = ''
        for attribute, value in sorted(data.items()):
            try:
                for attributes, values in value.items():
                    string += "<tr><td>%s - %s</td><td>%s</td></tr>" % (
                        attribute.capitalize(),
                        attributes.capitalize(),
                        str(values)
                    )
            except Exception:
                if value:
                    string += "<tr><td>%s</td><td>%s</td></tr>" % (attribute.capitalize(), str(value))

        return mark_safe("<table width='500px'>%s</table>" % string)

    def complete_booking(self, instance):

        if not instance.pk or instance.request_status == 6:
            return mark_safe("<p></p>")
        else:
            return mark_safe("<ul class='object-tools'>"
                             "<li><a href='#' booking_id='%d' class='historylink' id='BookingId'>Complete video booking</a></li>"
                             "</ul>" % instance.pk)


admin.site.register(BookingAdminAdd, BookingsAddOnlyAdmin)
admin.site.register(Reaction, ReactionsAdmin)
admin.site.register(Comment, CommentsAdmin)
admin.site.register(ReportAbuse, AbuseAdmin)
admin.site.register(Occasion, OccasionAdmin)
admin.site.register(Stargramrequest, StargramrequestAdmin)
admin.site.register(StargramVideo, StargramVideosAdmin)
admin.site.register(OccasionRelationship, OcccassionRelationshipAdmin)
admin.site.register(ReactionAbuse, ReactionAbuseAdmin)
