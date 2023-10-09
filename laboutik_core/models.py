from django.contrib.auth.models import AbstractUser
from django.db import models
from uuid import uuid4
from stdimage import JPEGField
from stdimage.validators import MinSizeValidator


# Create your models here.


class CustomUser(AbstractUser):
    """
    Modèle de base pour les utilisateurs
    On utilise des uuid4 plutôt que des pk auto-incrementés
    """
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False, db_index=False)
    email = models.EmailField(max_length=100, unique=True)
    image = JPEGField(upload_to="users_images", null=True, blank=True,
                  validators=[MinSizeValidator(540, 540)],
                  variations={
                      'bg_crop': (1080, 1080, True),
                      'md_crop': (540, 540, True),
                      'sm_crop': (270, 270, True)
                  },
                  delete_orphans=True,
                  verbose_name="Image de profil de l'utilisateur",
                  )

    LEVELING_CHOICES = (
        (1, "Commun"),
        (2, "Padawan"),
        (3, "Jedi"),
        (4, "Sith"),
    )

    leveling = models.PositiveIntegerField(choices=LEVELING_CHOICES, default=1)


### OBJETS DU POINTS DE VENTE ###


class Category(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False, db_index=False)
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default="#000000")
    #TODO : Integrer les SVG
    image = JPEGField(upload_to="categories", null=True, blank=True,
                      validators=[MinSizeValidator(540, 540)],
                      variations={
                          'bg_crop': (1080, 1080, True),
                          'md_crop': (540, 540, True),
                          'sm_crop': (270, 270, True)
                      },
                      delete_orphans=True,
                      verbose_name="Image de la catégorie",
                      )

    def __str__(self):
        return self.name

class Product(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False, db_index=False)
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category,
                                 on_delete=models.SET_NULL,
                                 related_name="products",
                                 null=True, blank=True,
                                 verbose_name="Catégorie")

    image = JPEGField(upload_to="categories", null=True, blank=True,
                      validators=[MinSizeValidator(540, 540)],
                      variations={
                          'bg_crop': (1080, 1080, True),
                          'md_crop': (540, 540, True),
                          'sm_crop': (270, 270, True)
                      },
                      delete_orphans=True,
                      verbose_name="Image du produit",
                      )

    def __str__(self):
        return self.name

class Price(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False, db_index=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="prices")
    name = models.CharField(max_length=100, null=True, blank=True)
    price = models.PositiveIntegerField(verbose_name="Prix")

    def __str__(self):
        if self.name:
            return f"{self.name} : {self.price}€"
        else:
            return f"{self.product.name} : {self.price}€"
