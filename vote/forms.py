from django import forms
from django.core.validators import validate_email

from vote.models import ManualVote

import urllib2


def email_or_twitter(address):
    try:
        validate_email(address)
    except forms.ValidationError:
        try:
            # ISSUE #1
            response = urllib2.urlopen('http://api.twitter.com/1/users/show.xml?screen_name=%s' % urllib2.quote(address.lstrip('@')))
        except urllib2.HTTPError:
            raise forms.ValidationError('Enter a valid email address or twitter username')

class EmailOrTwitterField(forms.EmailField):
    default_error_messages = {
            'invalid': u'Enter a valid email address or Twitter username',
            }
    default_validators = [email_or_twitter]

class SearchForm(forms.Form):
    q = forms.CharField()

class RequestForm(forms.Form):
    title = forms.CharField(required=False)
    artist = forms.CharField(required=False)
    show = forms.CharField(label="Source Anime", required=False)
    role = forms.CharField(label="Role (OP/ED/Insert/Character/etc.)", required=False)
    details = forms.CharField(widget=forms.Textarea, label="Additional Details", required=False)
    contact = EmailOrTwitterField(label="Email Address/Twitter name", required=True)

    def clean(self):
        cleaned_data = super(RequestForm, self).clean()

        filled = [cleaned_data[f] for f in cleaned_data if f != 'contact' and cleaned_data[f]]

        if len(filled) < 3:
            raise forms.ValidationError("I'm sure you can give us more information than that.")

        return cleaned_data

class LibraryUploadForm(forms.Form):
    library_xml = forms.FileField(label='Library XML')

class ManualVoteForm(forms.ModelForm):
    """ Make a manual vote! """
    class Meta:
        model = ManualVote


class BlockForm(forms.Form):
    """ Block something """
    reason = forms.CharField(max_length=256)

