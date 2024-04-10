from django.db import models
from cryptography.hazmat.primitives import serialization
# from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from uuid import uuid4
# Create your models here.
from django.contrib.auth.models import AbstractUser



class TibiUser(AbstractUser):
    #Pour avoir acces aux pages admin root et staff :
    is_superstaff = models.BooleanField(default=False)
    public_pem = models.CharField(max_length=512, editable=False, blank=True, null=True)
    uuid = models.UUIDField(editable=False, default=uuid4)

    def get_public_key(self):
        # Charger la clé publique au format PEM
        public_key = serialization.load_pem_public_key(
            self.public_pem.encode('utf-8'),
            backend=default_backend()
        )
        return public_key


