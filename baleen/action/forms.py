from django import forms

from baleen.action.actions import ExpectedActionOutput


class RemoteSSHActionForm(forms.Form):
    output_UX = forms.CharField(required=False)
    output_CX = forms.CharField(required=False)
    output_CH = forms.CharField(required=False)

    def save(self, *args, **kwargs):
        action = super(RemoteSSHActionForm, self).save(*args, **kwargs)
        
        # For each output type, check if one exists for action.
        # Change, create, or delete as necessary
        d = self.cleaned_data
        for output_type in ['UX', 'CX', 'CH']:
            field_name = 'output_' + output_type
            val = d.get(field_name)
            action = ExpectedActionOutput(action, output_type, val)
        return action
