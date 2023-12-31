from django.contrib import admin
from .models import CelebrityDisplay, CelebrityDisplayOrganizer, HomePageVideo, CelebrityDashboard, Tag
from utilities.admin_utils import ReadOnlyModelAdmin
from users.models import Profession, StargramzUser
from django import forms
from django.shortcuts import redirect
from dal import autocomplete, forward
from utilities.utils import get_pre_signed_get_url
from config.models import Config
from job.tasks import generate_medium_thumbnail


class CelebrityDisplayAdminInline(admin.StackedInline):
    model = CelebrityDisplay
    autocomplete_fields = ['celebrity']
    min_num = 1
    readonly_fields = ('order',)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        if CelebrityDisplay.objects.all().count() >= 41:
            return False
        return True

    def get_min_num(self, request, obj=None, **kwargs):
        if obj and not obj.profession:
            if obj.featured:
                return 1
            return 5
        else:
            return 1

    def get_max_num(self, request, obj=None, **kwargs):
        if obj and not obj.profession:
            if obj.featured:
                return 4
            return 9
        else:
            return 4

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        url = request.get_full_path()
        data = url.split("/")
        try:
            obj_id = int(data[4])
            obj = CelebrityDisplayOrganizer.objects.get(id=obj_id)
            profession = obj.profession
        except Exception as e:
            print(str(e))
            profession = None

        if db_field.name == "celebrity":
            if not profession:
                return CelebrityChoiceField(StargramzUser.objects.all(), required=False, widget=autocomplete.ModelSelect2(url='user_autocomplete'))
            else:
                return CelebrityChoiceField(StargramzUser.objects.all(), required=False, widget=autocomplete.ModelSelect2(url='user_autocomplete', forward=(forward.Const(profession.id, 'profession'), )))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ProfessionFilter(admin.SimpleListFilter):

    title = 'Profession'
    parameter_name = 'profession'

    def lookups(self, request, model_admin):

        return (
            ('Featured', 'Featured'),
            ('Sports', 'Sports'),
            ('Movies / TV', 'Movies/TV'),
            ('Music', 'Music'),
            ('Radio / Podcast', 'Radio/Podcast'),
            ('Social / Youtube', 'Social/Youtube'),
            ('Comedians', 'Comedians'),
            ('Everyday Stars', 'Everyday Stars'),
            ('Imitators', 'Imitators'),
        )

    def queryset(self, request, queryset):

        if self.value() is None:
            return queryset.filter(celebrity_display__profession=None, celebrity_display__featured=False).exclude(celebrity=None)
        elif self.value() == 'Featured':
            return queryset.filter(celebrity_display__profession=None, celebrity_display__featured=True).exclude(celebrity=None)
        else:
            return queryset.filter(celebrity_display__profession__title=self.value()).exclude(celebrity=None)

    def choices(self, changelist):
        print(changelist.get_query_string(remove=[self.parameter_name]))
        yield {
            'selected': self.value() is None,
            'query_string': changelist.get_query_string(remove=[self.parameter_name]),
            'display': '9star'
        }
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == str(lookup),
                'query_string': changelist.get_query_string({self.parameter_name: lookup}),
                'display': title,
            }


class CelebrityDisplayAdmin(ReadOnlyModelAdmin):
    list_display = ('celebrity', 'name', 'order', 'profession')
    ordering = ('id',)
    list_filter = (ProfessionFilter,)

    def profession(self, instance):
        if instance.celebrity_display and instance.celebrity_display.profession:
            return instance.celebrity_display.profession.title
        else:
            return None

    def name(self, instance):
        if instance.celebrity:
            return instance.celebrity.get_short_name()
        else:
            return "No celebrity selected"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return True


class CelebrityDisplayOrganizerForm(forms.ModelForm):
    class Meta:
        model = CelebrityDisplayOrganizer
        fields = '__all__'

    def clean(self):
        celebrity_display_element = []
        if not self.cleaned_data["title"]:
            raise forms.ValidationError("Error  : Title is empty")
        if len(self.changed_data) is 1 and 'title' in self.changed_data:
            celebrity_display_organizer = CelebrityDisplayOrganizer.objects.filter(
                profession=self.cleaned_data["profession"], featured=self.cleaned_data["featured"]
            )
            if celebrity_display_organizer.count() > 0 and celebrity_display_organizer[0].id is not self.instance.id:
                raise forms.ValidationError("Error  : 9 star list already exist")
            return self.cleaned_data
        if self.has_changed():
            celebrity_display_organizer = CelebrityDisplayOrganizer.objects.filter(
                profession=self.cleaned_data["profession"], featured=self.cleaned_data["featured"]
            ).count()
            if celebrity_display_organizer > 0:
                if self.cleaned_data["featured"]:
                    raise forms.ValidationError("Error  : Featured List already exist")
                elif not self.cleaned_data["profession"]:
                    raise forms.ValidationError("Error  : 9 star list already exist")
                else:
                    raise forms.ValidationError("Error  : This profession already exist")
            if self.cleaned_data["featured"] and self.cleaned_data["profession"]:
                raise forms.ValidationError("Error  : Featured List must not have profession")
        if self.data.get("profession", None) or self.data.get("featured", None):
            limit = 4
        else:
            limit = 9
        for i in range(limit):
            element = self.data.get("celebrity_display_organizer-%s-celebrity" % i)
            if element is "":
                pass
            else:
                celebrity_display_element.append(element)
        if len(celebrity_display_element) > len(set(celebrity_display_element)) and len(self.data) > 5:
            raise forms.ValidationError("Error  : Celebrity repetition is not allowed")

        return self.cleaned_data


class CelebrityDisplayOrganizerAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'title', 'profession', 'featured')
    fieldsets = (
        (None, {'fields': ('title', 'profession', 'featured')}),
    )
    ordering = ('id',)
    inlines = []
    inlines2 = [CelebrityDisplayAdminInline]
    form = CelebrityDisplayOrganizerForm

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'profession':
            return ProfessionChoiceField(queryset=Profession.objects.filter(parent=None), required=False)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_inline_instances(self, request, obj=None):
        if obj:
            return [inline(self.model, self.admin_site) for inline in self.inlines2]
        return [inline(self.model, self.admin_site) for inline in self.inlines]

    def response_add(self, request, obj, post_url_continue=None):

        if obj.profession:
            for i in range(1, 5):
                CelebrityDisplay.objects.create(celebrity=None, celebrity_display=obj, order=i)
        elif obj.featured:
            for i in range(1, 5):
                CelebrityDisplay.objects.create(celebrity=None, celebrity_display=obj, order=i)
        else:
            for i in range(1, 10):
                CelebrityDisplay.objects.create(celebrity=None, celebrity_display=obj, order=i)
        return redirect("/admin/users2/celebritydisplayorganizer/%s/change/" % str(obj.id))

    def response_change(self, request, obj):
        return redirect("/admin/users2/celebritydisplayorganizer/%s/change/" % str(obj.id))

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        if change:
            if obj.profession:
                type_of_picture = 2
            elif obj.featured:
                type_of_picture = 2
            else:
                type_of_picture = 1
            context['adminform'].form.fields['featured'].help_text = self.picture_display(type_of_picture)
        return super().render_change_form(request, context, add, change, form_url, obj)

    def picture_display(self, type_of_picture=1):
        if type_of_picture == 1:
            return "<img src='/media/web-images/celebrity_display_position.png' style='margin-left: -20px'>"
        else:
            return "<img src='/media/web-images/4star_celebrity_display.png' style='margin-left: -20px'>"

    picture_display.allow_tags = True

    def save_related(self, request, obj, form, change):
        super().save_related(request, obj, form, change)
        celebrity_ids = [item.celebrity.id for item in CelebrityDisplay.objects.filter(
            celebrity_display_id=obj.instance.id, celebrity__isnull=False).all().iterator()
        ]
        generate_medium_thumbnail.delay(celebrity_ids)


class ProfessionChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return "{}".format(obj.title)


class CelebrityChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return "{}".format(obj.get_short_name())


class HomePageVideoAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_date', 'modified_date')

    def name(self, obj):
        return obj.video.name.split("/")[-1]

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        if change:
            video = Config.objects.get(key='home_page_videos').value
            url = get_pre_signed_get_url(obj.video.name.split("/")[-1], video)
            context['adminform'].form.fields['video'].help_text = self.picture_display(url)
        return super().render_change_form(request, context, add, change, form_url, obj)

    def picture_display(self, url):
        return "<video width='320' height='240' controls><source src='%s' type='video/mp4'>" % url

    def has_add_permission(self, request):
        if HomePageVideo.objects.all().count() >= 2:
            return False
        else:
            return True


class CelebrityProfileShareAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'share_type', 'video', 'created_date')

    def username(self, obj):
        return obj.user.get_short_name()


class CelebrityDashboardAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'last_updated_by_update_API')
    search_fields = ('user__first_name', 'user__last_name', 'user__nick_name', 'user__email',)


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ('name',)

    def clean(self):
        tag_name = self.cleaned_data['name']
        if tag_name and Tag.objects.filter(name__iexact=tag_name).exists():
            raise forms.ValidationError('A tag with this name already exists.')


class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    ordering = ('id',)
    form = TagForm


admin.site.register(HomePageVideo, HomePageVideoAdmin)
admin.site.register(CelebrityDisplay, CelebrityDisplayAdmin)
admin.site.register(CelebrityDisplayOrganizer, CelebrityDisplayOrganizerAdmin)
admin.site.register(CelebrityDashboard, CelebrityDashboardAdmin)
admin.site.register(Tag, TagAdmin)
