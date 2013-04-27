import re

import tweepy

from django import forms
from django.core.validators import validate_email
from django.conf import settings
from django.utils.safestring import mark_safe

from vote.models import ManualVote
from vote import trivia


post_tw_auth = tweepy.OAuthHandler(settings.CONSUMER_KEY,
                                   settings.CONSUMER_SECRET)
post_tw_auth.set_access_token(settings.POSTING_ACCESS_TOKEN,
                              settings.POSTING_ACCESS_TOKEN_SECRET)
tw_api = tweepy.API(post_tw_auth)


def email_or_twitter(address):
    try:
        validate_email(address)
    except forms.ValidationError:
        try:
            tw_api.get_user(screen_name=address.lstrip('@'))
        except tweepy.TweepError:
            raise forms.ValidationError(
                'Enter a valid email address or twitter username')


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
    role = forms.CharField(label="Role (OP/ED/Insert/Character/etc.)",
                           required=False)
    details = forms.CharField(widget=forms.Textarea,
                              label="Additional Details", required=False)
    contact = EmailOrTwitterField(label="Email Address/Twitter name",
                                  required=True)
    trivia_question = forms.CharField(widget=forms.HiddenInput)
    trivia = forms.CharField(required=True)

    def clean(self):
        cleaned_data = super(RequestForm, self).clean()

        compulsory = ['trivia', 'trivia_question', 'contact']

        filled = [cleaned_data[f] for f in cleaned_data
                  if f not in compulsory and cleaned_data[f]]

        if len(filled) < 2:
            raise forms.ValidationError(
                "I'm sure you can give us more information than that.")

        human = re.match(
            trivia.questions[cleaned_data['trivia_question']] + '$',
            cleaned_data['trivia'], re.I)

        hint = (
            "That's not right, sorry. There are hints <a href='https://github"
            ".com/colons/nkdsu/blob/master/vote/trivia.py'>here</a>."
        )

        if not human:
            self._errors['trivia'] = self.error_class([mark_safe(hint)])

        return cleaned_data


class LibraryUploadForm(forms.Form):
    library_xml = forms.FileField(label='Library XML')
    inudesu = forms.BooleanField(label='Inu Desu', required=False)


class ManualVoteForm(forms.ModelForm):
    """ Make a manual vote! """

    class Meta:
        model = ManualVote


class BlockForm(forms.Form):
    """ Block something """
    reason = forms.CharField(max_length=256)
