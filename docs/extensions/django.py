import inspect
from django import forms
from django.db import models
from django.utils.html import strip_tags
from django.utils.encoding import force_text

_field_module_map = {
    'django.forms.fields': 'django.forms',
    'django.forms.models': 'django.forms',
    'django.db.models.fields': 'django.db.models',
}


def process_docstring(app, what, name, obj, options, lines):
    # Only look at objects that inherit from Django's base model class
    if inspect.isclass(obj) and (
            issubclass(obj, models.Model) or
            issubclass(obj, forms.ModelForm)):
        # Grab the field list from the meta class
        fields = obj._meta.fields

        for field in fields:
            if isinstance(field, str):
                attname = field
                field = obj.base_fields[attname]
            else:
                attname = field.attname

            # Decode and strip any html out of the field's help text
            help_text = strip_tags(force_text(field.help_text))

            # Decode and capitalize the verbose name, for use if there isn't
            # any help text
            verbose_name = force_text(
                getattr(field, 'verbose_name', getattr(field, 'label', field))
            ).capitalize()

            if help_text:
                # Add the model field to the end of the docstring as a param
                # using the help text as the description
                lines.append(':param %s: %s' % (attname, help_text))
            else:
                # Add the model field to the end of the docstring as a param
                # using the verbose name as the description
                lines.append(':param %s: %s' % (attname, verbose_name))

            # Add the field's type to the docstring
            if isinstance(field, models.ForeignKey):
                to = field.rel.to

                if isinstance(to, str):
                    module, name = to.split('.')
                else:
                    module, name = to.__module__, to.__name__
                lines.append(
                    ':type %s: %s to :class:`~%s.%s`' %
                    (attname, type(field).__name__, module, name)
                )

            else:
                field_cls = type(field)
                module, name = field_cls.__module__, field_cls.__name__
                module = _field_module_map.get(module, module)
                lines.append(
                    ':type %s: :class:`~%s.%s`' %
                    (attname, module, name)
                )

    # Return the extended docstring
    return lines


def setup(app):
    # Register the docstring processor with sphinx
    app.connect('autodoc-process-docstring', process_docstring)
