from django import forms

from baleen.action.models import RemoteSSHAction
from baleen.artifact.models import ExpectedActionOutput

class RemoteSSHActionForm(forms.ModelForm):
    output_UX = forms.CharField(required=False)
    output_CX = forms.CharField(required=False)
    output_CH = forms.CharField(required=False)

    #def clean_output_UX(self):
        #ux = self.cleaned_data['output_UX']
        #return ux

    def save(self, *args, **kwargs):
        action = super(RemoteSSHActionForm, self).save(*args, **kwargs)
        
        # For each output type, check if one exists for action.
        # Change, create, or delete as necessary
        d = self.cleaned_data
        for output_type in ['UX', 'CX', 'CH']:
            field_name = 'output_' + output_type
            val = d.get(field_name)
            e = None
            try:
                e = ExpectedActionOutput.objects.get(action=action, output_type=output_type)
                if not val:
                    e.delete()
            except ExpectedActionOutput.DoesNotExist:
                if val:
                    e = ExpectedActionOutput(action=action, output_type=output_type)
            if val:
                e.location = val
                e.save()
        return action
        

    class Meta:
        model = RemoteSSHAction
