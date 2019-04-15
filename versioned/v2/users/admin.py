from django.contrib import admin
from .models import CelebrityDisplay, CelebrityDisplayOrganizer
from utilities.admin_utils import ReadOnlyModelAdmin
from users.models import Profession, StargramzUser
from django import forms
from django.shortcuts import redirect

class CelebrityDisplayAdminInline(admin.StackedInline):
    model = CelebrityDisplay
    autocomplete_fields = ['celebrity']
    min_num = 1

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        if CelebrityDisplay.objects.all().count() >= 41:
            return False
        return True

    def get_min_num(self, request, obj=None, **kwargs):
        if obj and not obj.profession:
            return 5
        else:
            return 1

    def get_max_num(self, request, obj=None, **kwargs):
        if obj and not obj.profession:
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
                return CelebrityChoiceField(queryset=StargramzUser.objects.filter(
                    celebrity_user__admin_approval=True), required=False)
            else:
                return CelebrityChoiceField(queryset=StargramzUser.objects.filter(
                    celebrity_user__admin_approval=True, celebrity_profession__profession=profession), required=False)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ProfessionFilter(admin.SimpleListFilter):

    title = 'Profession'
    parameter_name = 'profession'

    def lookups(self, request, model_admin):

        return (
            ('star', '9star'),
            ('Sports', 'sports'),
            ('Movies / TV', 'Movies/TV'),
            ('Music', 'Music'),
            ('Radio / Podcast', 'Radio/Podcast'),
            ('Social / Youtube', 'Social/Youtube'),
            ('Comedians', 'Comedians'),
            ('Everyday Stars', 'Everyday Stars'),
            ('Impersonators', 'Impersonators'),
        )

    def queryset(self, request, queryset):

        if self.value() == 'star':
            return queryset.filter(celebrity_display__profession=None)
        else:
            return queryset.filter(celebrity_display__profession__title=self.value())


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
        return instance.celebrity.get_short_name()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return True


class CelebrityDisplayOrganizerAdmin(ReadOnlyModelAdmin):
    list_display = ('id', 'title', 'profession')
    fieldsets = (
        (None, {'fields': ('title', 'profession')}),
    )
    ordering = ('id',)
    inlines = []
    inlines2 = [CelebrityDisplayAdminInline]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'profession':
            return ProfessionChoiceField(queryset=Profession.objects.filter(parent=None), required=False)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_inline_instances(self, request, obj=None):
        if obj:
            return [inline(self.model, self.admin_site) for inline in self.inlines2]
        return [inline(self.model, self.admin_site) for inline in self.inlines]

    def response_add(self, request, obj, post_url_continue=None):
        return redirect("/admin/users2/celebritydisplayorganizer/%s/change/" % str(obj.id))

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        if change:
            if obj.profession:
                type_of_picture = 2
            else:
                type_of_picture = 1
            context['adminform'].form.fields['profession'].help_text = self.picture_display(type_of_picture)
        return super().render_change_form(request, context, add, change, form_url, obj)

    def picture_display(self, type_of_picture=1):
        if type_of_picture == 1:
            return "<img src='/media/web-images/celebrity_display_position.png' style='margin-left: -180px'>"
        else:
            return "<img src='/media/web-images/4star_celebrity_display.png' style='margin-left: -180px'>"

    picture_display.allow_tags = True


class ProfessionChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return "{}".format(obj.title)

class CelebrityChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return "{}".format(obj.get_short_name())


admin.site.register(CelebrityDisplay, CelebrityDisplayAdmin)
admin.site.register(CelebrityDisplayOrganizer, CelebrityDisplayOrganizerAdmin)
