import re
from random import choice
from typing import Any, Optional

from django import forms
from django.utils.safestring import mark_safe

from .models import Note, Request, Track, Vote
from ..vote import trivia

_disable_autocorrect = {
    "autocomplete": "off",
    "autocorrect": "off",
    "spellcheck": "false",
}

_proper_noun_textinput = forms.TextInput(
    attrs=dict(_disable_autocorrect, autocapitalize="words")
)


class SearchForm(forms.Form):
    q = forms.CharField()


class TriviaForm(forms.Form):
    """
    A form protected by a trivia question.
    """

    trivia_question = forms.CharField(widget=forms.HiddenInput)
    trivia = forms.CharField(required=False)

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


class BadMetadataForm(forms.Form):
    details = forms.CharField(
        widget=forms.Textarea, label="What needs fixing?", required=False
    )
    track: Track

    def __init__(self, *args, track: Track, **kwargs) -> None:
        self.track = track
        super().__init__(*args, **kwargs)


class RequestForm(forms.Form):
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

    def clean(self) -> Optional[dict[str, Any]]:
        cleaned_data = super().clean()
        if cleaned_data is None:
            return None

        filled = [cleaned_data[f] for f in cleaned_data if cleaned_data[f]]

        if len(filled) < 1:
            raise forms.ValidationError(
                'please provide at least some information to work with'
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
