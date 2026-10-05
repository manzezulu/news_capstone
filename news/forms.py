"""Forms for registration, articles and newsletters."""

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Article, CustomUser, Newsletter

INPUT_CLASS = 'form-control'
SELECT_CLASS = 'form-select'


class RegistrationForm(UserCreationForm):
    """Sign-up form that also captures email and role."""

    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'role')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', SELECT_CLASS)
            else:
                widget.attrs.setdefault('class', INPUT_CLASS)
        # Autocomplete hints
        self.fields['username'].widget.attrs['autocomplete'] = 'username'
        self.fields['email'].widget.attrs.update({
            'autocomplete': 'email',
            'spellcheck': 'false',
        })
        self.fields['password1'].widget.attrs['autocomplete'] = 'new-password'
        self.fields['password2'].widget.attrs['autocomplete'] = 'new-password'


class ArticleForm(forms.ModelForm):
    """Journalists/editors edit title, content and optional publisher."""

    class Meta:
        model = Article
        fields = ('title', 'content', 'publisher')

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        if user.role == CustomUser.Role.JOURNALIST:
            self.fields['publisher'].queryset = user.publishers_written_for.all()
        self.fields['publisher'].required = False
        self.fields['publisher'].empty_label = 'Independent (no publisher)'
        self.fields['title'].widget.attrs.update({
            'class': INPUT_CLASS,
            'placeholder': 'An engaging headline…',
            'autocomplete': 'off',
        })
        self.fields['content'].widget.attrs.update({
            'class': INPUT_CLASS,
            'rows': 12,
            'placeholder': 'Write your article…',
        })
        self.fields['publisher'].widget.attrs['class'] = SELECT_CLASS


class NewsletterForm(forms.ModelForm):
    """Newsletter fields with a checkbox list of approved articles."""

    class Meta:
        model = Newsletter
        fields = ('title', 'description', 'articles')
        widgets = {'articles': forms.CheckboxSelectMultiple}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['articles'].queryset = Article.objects.filter(approved=True)
        self.fields['title'].widget.attrs.update({
            'class': INPUT_CLASS,
            'placeholder': 'Newsletter title…',
        })
        self.fields['description'].widget.attrs.update({
            'class': INPUT_CLASS,
            'rows': 4,
            'placeholder': 'What is this newsletter about…',
        })
