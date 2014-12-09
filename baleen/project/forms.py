from django import forms

from crispy_forms.helper import FormHelper

from baleen.project.models import Project

class ProjectForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_method = 'post'
        self.helper.help_text_inline = True

        super(ProjectForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Project
        #fields = ['pub_date', 'headline', 'content', 'reporter']
        exclude = ['github_token', 'private_key']
