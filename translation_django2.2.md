# Traduction django 2.2:
https://docs.djangoproject.com/fr/2.2/topics/i18n/translation/#how-django-discovers-language-preference

## settings.py
		MIDDLEWARE = [
			'django.contrib.sessions.middleware.SessionMiddleware',
			'django.middleware.locale.LocaleMiddleware',
			'django.middleware.common.CommonMiddleware',
		]

		LANGUAGE_CODE = os.environ.get('LANGUAGE_CODE', 'fr')
		TIME_ZONE = os.environ.get('TIME_ZONE', 'Indian/Reunion')

		USE_I18N = True
		USE_L10N = True
		USE_TZ = True

		LOCALE_PATHS = (
				os.path.join(BASE_DIR, 'locale'),
		)
	
## views.py
		from django.utils.translation import ugettext_lazy as _

## Template
```
{% load i18n %}
<div class="sous-element-texte">{% trans 'RETOUR' %}</div>
```

## Fichiers de traduction *.po

### rootApp/locale/en/LC_MESSAGES/django.po
```
#: webview/templates/elements/bouton_return:39
msgid "RETOUR"
msgstr "RETURN"
```

### rootApp/locale/en/LC_MESSAGES/django.po
```
#: webview/templates/elements/bouton_return:39
msgid "RETOUR"
msgstr ""
```

### Après chaque modifications des fichier *.po
```
django-admin compilemessages
```

## Changement langue à partir du front
```
// POST le changement de langue au serveur et recharge la page
const selectLanguage = 'fr'
// <input type="hidden" name="csrfmiddlewaretoken" value="0CaEpgyxLdl1m2NEP7W1fCo0esIWDvaGvvFioVMBstsj2GwkFcBCwQyDsEnCg0LZ">
csrf_token = document.querySelector('input[name="csrfmiddlewaretoken"]')
try {
    const body = new URLSearchParams()
    body.append('csrfmiddlewaretoken', csrf_token)
    body.append('language', selectLanguage)
    const response = await fetch(`/i18n/setlang/`, { method: 'post', body })
    if (response.status === 200) {
        window.location.reload()
    } else {
        throw Error(data.message)
    }
} catch (error) {
    console.log('-> fetcht  =', error)
}
```
