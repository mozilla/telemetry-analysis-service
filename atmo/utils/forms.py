from django import forms


class CreatedByFormMixin(object):

    def __init__(self, user, *args, **kwargs):
        self.created_by = user
        super(CreatedByFormMixin, self).__init__(*args, **kwargs)

    def clean(self):
        """
        only allow deleting clusters that one created
        """
        super(CreatedByFormMixin, self).clean()
        if self.instance.id and self.created_by != self.instance.created_by:
            raise forms.ValidationError(
                "Access denied to a cluster of another user"
            )
