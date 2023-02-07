import re
from random import choice
from typing import Any, Optional

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import validate_email
from django.utils.safestring import mark_safe
import tweepy

from .models import Note, Request, Vote
from .utils import reading_tw_api
from ..vote import trivia

_disable_autocorrect = {
    "autocomplete": "off",
    "autocorrect": "off",
    "spellcheck": "false",
}

_proper_noun_textinput = forms.TextInput(
    attrs=dict(_disable_autocorrect, autocapitalize="words")
)


def email_or_twitter(address: str) -> None:
    try:
        validate_email(address)
    except forms.ValidationError:
        try:
            reading_tw_api.get_user(screen_name=address.lstrip('@'))
        except tweepy.TweepError:
            raise forms.ValidationError(
                'Enter a valid email address or twitter username'
            )


class EmailOrTwitterField(forms.EmailField):
    widget = forms.TextInput(attrs=dict(_disable_autocorrect, autocapitalize="off"))
    default_error_messages = {
        'invalid': u'Enter a valid email address or Twitter username',
    }
    default_validators = [email_or_twitter]


class SearchForm(forms.Form):
    q = forms.CharField()


class TriviaForm(forms.Form):
    """
    A form protected by a trivia question.
    """

    trivia_question = forms.CharField(widget=forms.HiddenInput)
    trivia = forms.CharField(required=False)
    track = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.order_fields([k for k in self.fields.keys() if k != 'trivia'] + ['trivia'])
        self.fields['trivia_question'].initial = self.new_question()

    def new_question(self) -> str:
        question = choice(list(trivia.questions.keys()))
        self.fields['trivia'].label = 'Captcha: %s' % question
        return question

    def clean_trivia(self):
        human = True

        if 'trivia' in self.cleaned_data:
            human = re.match(
                trivia.questions[self.cleaned_data['trivia_question']] + '$',
                self.cleaned_data['trivia'],
                re.I,
            )

        request = Request()
        request.successful = bool(human)
        if self.track:
            request.track_id = self.track.pk
        request.serialise(self.cleaned_data)
        request.save()

        if not human:
            hint = (
                "That's not right, sorry. There are hints <a href='https://"
                "github.com/very-scary-scenario/nkd.su/blob/master/nkdsu/apps/"
                "vote/trivia.py'>here</a>."
            )
            mutable = self.data._mutable
            self.data._mutable = True
            self.data['trivia_question'] = self.new_question()
            self.data._mutable = mutable
            raise forms.ValidationError([mark_safe(hint)])

        return self.cleaned_data['trivia']


class BadMetadataForm(TriviaForm):
    details = forms.CharField(
        widget=forms.Textarea, label="What needs fixing?", required=False
    )
    contact = EmailOrTwitterField(label="Email/Twitter (not required)", required=False)

    def __init__(self, *args, **kwargs) -> None:
        self.track = kwargs.pop('track')
        super().__init__(*args, **kwargs)


class RequestForm(TriviaForm):
    """
    A form for requesting that a track be added to the library.
    """

    title = forms.CharField(widget=_proper_noun_textinput, required=False)
    artist = forms.CharField(widget=_proper_noun_textinput, required=False)
    show = forms.CharField(
        label="Source Anime", required=False, widget=_proper_noun_textinput
    )
    role = forms.CharField(label="Role (OP/ED/Insert/Character/etc.)", required=False)
    details = forms.CharField(
        widget=forms.Textarea(attrs=_disable_autocorrect),
        label="Additional Details",
        required=False,
    )
    contact = EmailOrTwitterField(label="Email Address/Twitter name", required=True)

    def clean(self) -> Optional[dict[str, Any]]:
        cleaned_data = super().clean()
        if cleaned_data is None:
            return None

        compulsory = Request.METADATA_KEYS

        filled = [
            cleaned_data[f]
            for f in cleaned_data
            if f not in compulsory and cleaned_data[f]
        ]

        if len(filled) < 2:
            raise forms.ValidationError(
                "I'm sure you can give us more information than that."
            )

        return cleaned_data


class VoteForm(forms.ModelForm):
    """
    A form for creating a :class:`.models.Vote`.
    """

    class Meta:
        model = Vote
        fields = ['text']
        widgets = {
            'text': forms.TextInput(),
        }


class CheckMetadataForm(forms.Form):
    id3_title = forms.CharField(required=False, widget=forms.Textarea())
    id3_artist = forms.CharField(required=False, widget=forms.Textarea())
    composer = forms.CharField(required=False, widget=forms.Textarea())
    year = forms.IntegerField(required=False)


class LibraryUploadForm(forms.Form):
    library_xml = forms.FileField(label='Library XML')
    inudesu = forms.BooleanField(label='Inu Desu', required=False)


class NoteForm(forms.ModelForm):
    just_for_current_show = forms.BooleanField(required=False)

    class Meta:
        model = Note
        fields = ['content', 'public']


class DarkModeForm(forms.Form):
    mode = forms.ChoiceField(
        choices=[
            ('light', 'light'),
            ('dark', 'dark'),
            ('system', 'system'),
        ]
    )


class RegistrationForm(UserCreationForm):
    def clean_username(self):
        raise NotImplementedError()
