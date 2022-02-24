# -*- coding: utf-8 -*-
from django.forms import ModelForm, FileField
from .models import ProcessUpdateItem
from .validators import csv_content_validator
from django.core.exceptions import ValidationError
from .services import Alma_Apis
from django.conf import settings
import logging

#Initialisation des logs
logger = logging.getLogger(__name__)

class UploadFileForm(ModelForm):
    file_upload = FileField(label='Télécharger le fichier à traiter', validators=[csv_content_validator])
    class Meta:
        model = ProcessUpdateItem
        fields = ['institution', 'base', 'file_upload']

    def clean(self) :
        # cleaned_data = super().clean()
        institution = self.cleaned_data.get("institution")
        base = self.cleaned_data.get("base")
        file = self.cleaned_data.get('file_upload')
        # Teste si institution possède bien une base de test
        if base == 'TEST' and institution in ('INP','IEP'):
            raise ValidationError('Nous ne disposons pas de bac à sable pour l''institution {}'.format(institution))
        # Teste si un autre process est en cours 
        if ProcessUpdateItem.objects.filter(is_done=False).count() > 0 :
            raise ValidationError('Un autre processus est en cours attendez la fin de son exécution pour lancer un nouveau traitement')
        # Teste s'il reste suffisamment d'appels d'Api autorisés pour lancer le traitement sur toutes les lignes du fichier
        alma_api = Alma_Apis.AlmaRecords(apikey=settings.ALMA_API_KEY[institution], region='EU', service=__name__)
        status,nb_api_call = alma_api.get_api_remaining()
        if status == "Error" :
            # Pb. de clef où indisponibilité du service
            raise ValidationError("L'API Alma remonte l'erreur suivante :  {} . Contacter l'administrateur".format(nb_api_call))
        try:
            num_ligne = sum(1 for line in file) - 1  
        except :
            raise ValidationError("Le fichier doit être un fichier csv, txt ou tsv")
        
        logger.debug(num_ligne)
        if (num_ligne*3) > (int(nb_api_call) - 10000) :
            raise ValidationError("Nous ne disposons que de {} appels d'API pour la journée. Votre fichier contient {} lignes. Il faut deux appels par ligne pour traiter le fichier. Merci de diminuer le nombre de lignes à traiter".format(nb_api_call,num_ligne))
        # raise ValidationError("{}".format(num_ligne))
