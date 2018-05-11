from django.utils.text import capfirst
from django.apps import apps
from django.utils.safestring import mark_safe
from django.contrib.admin import ModelAdmin
from django.contrib import admin

# get_models returns all the models, but there are
# some which we would like to ignore
IGNORE_MODELS = (
    "auth",
    "sites",
    "sessions",
    "admin",
    "contenttypes",
)


def app_list(request):
    """
        Get all models and add them to the context apps variable.
    """
    user = request.user
    app_dict = {}
    admin_class = ModelAdmin
    for model in apps.get_models():
        model_admin = admin_class(model, None)
        app_label = model._meta.app_label
        if app_label in IGNORE_MODELS:
            continue
        if not admin.site.is_registered(model):
            continue
        has_module_perms = user.has_module_perms(app_label)
        if has_module_perms:
            perms = model_admin.get_model_perms(request)
            # Check whether user has any perm for this module.
            # If so, add the module to the model_list.
            if True in perms.values():
                model_dict = {
                    'name': capfirst(model._meta.verbose_name_plural),
                    'admin_url': mark_safe('%s/%s/' % (app_label, model.__name__.lower())),
                }
                if app_label in app_dict:
                    app_dict[app_label]['models'].append(model_dict)
                else:
                    app_dict[app_label] = {
                        'name': app_label.title(),
                        'app_url': app_label + '/',
                        'has_module_perms': has_module_perms,
                        'models': [model_dict],
                    }

    menu_values = app_dict.values()
    menu_list = sorted(menu_values, key=lambda k: k['name'])
    return {'apps': menu_list}
