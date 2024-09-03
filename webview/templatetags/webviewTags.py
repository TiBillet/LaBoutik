from django import template
# from django.template.defaultfilters import stringfilter

register = template.Library()

boutonLargeur = 134
boutonHauteur = 84

boutonsAction = {
    "validerCarteMaitresse":{
        "idFormulaire":"form_accueil",
        "lignes":['Passez votre carte','maîtresse','au-dessus du lecteur'],
        "tailleTexte":"1.8rem","couleur_texte":"#ffffff","couleur_backgr":"#337ab7",
        "largeur":"360px","hauteur":"200px",
        "id_contenu_bouton":"accueil-contenu-bouton"
    },
    "erreurCarteMaitresse":{
        "idFormulaire":"form_accueil",
        "fonction":"valider_formulaire_accueil(this)",
        "lignes":['Erreur:','Carte maîtresse','non valide.','Réessayez'],
        "tailleTexte":"1.8rem","couleur_texte":"#ffffff","couleur_backgr":"#d9534f",
        "largeur":"360px","hauteur":"200px"
    }
}

@register.filter
def gradient(valHexa,valAj):
    if valHexa != '':
        valAj = int(valAj)
        valHexa = valHexa.lstrip('#')
        rgb = tuple(int(valHexa[i:i+2], 16) for i in (0, 2, 4))
        val1 = 'rgb('+str(rgb[0])+','+str(rgb[1])+','+str(rgb[2])+')'
        if abs(valAj)>=0 and abs(valAj)<=255:
            r = int(rgb[0]+valAj)
            if r<0:
                r = 0
            if r>255:
                r=255
            v = int(rgb[1]+valAj)
            if v<0:
                v = 0
            if v>255:
                v=255
            b = int(rgb[2]+valAj)
            if b<0:
                b = 0
            if b>255:
                b=255
            val2 = 'rgb('+str(r)+','+str(v)+','+str(b)+')'
            return val2

        else:
            return val1
    else:
        return 'rgb(255,0,0)'

@register.inclusion_tag('boutonForm.html',takes_context=True)
def boutonForm(context):
    index = str(context['selBouton'])
    context['infosBouton']= boutonsAction[index]
    return context


@register.filter
def dec2(value):
    return f"{(int(value) / 100):.2f}"