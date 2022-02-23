from django.contrib import admin
from django.http import HttpResponse,HttpResponseRedirect
from django.urls import path
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.conf import settings
from .models import ProcessUpdateItem
from .forms import UploadFileForm
from .services import main, Alma_Apis
import logging
import threading

# Register your models here.

#Initialisation des logs
logger = logging.getLogger(__name__)

#Thread pour le lancement du traitement
class ExecuteJobThread(threading.Thread):

    def __init__(self,process):
        self.process = process
        threading.Thread.__init__(self)

    def run(self):
        logger.debug("Lancement du traitement ExecuteJobThread")
        main.handle_uploaded_file(self.process)
        logger.debug("Fin ExecuteJobThread")


@admin.register(ProcessUpdateItem)
class UpdateItemProcesss(admin.ModelAdmin):
    list_display = ('id', 'institution', 'base', 'start_date', 'end_date','num_title_to_processed', 'is_done','num_title_processed','link_file_download')
    ordering = ('start_date',)
    search_fields = ('file_upload',)
    fieldsets = (
        (None, {
            'fields': ('institution','base','file_upload' ),
            'description': ""
        }),
    )
    form = UploadFileForm

    def render_change_form(self, request, context, *args, **kwargs):
        # here we define a custom template
        self.change_form_template = 'alma_utils/message_aide.html'
        extra = {
            'help_text': "This is a help message. Good luck filling out the form."
        }

        context.update(extra)
        return super(UpdateItemProcesss, self).render_change_form(request,
            context, *args, **kwargs)


    def save_model(self, request, obj, form, change):
        # Teste s'il reste suffisamment d'appels d'Api autorisés pour lancer le traitement sur toutes les lignes du fichier
        alma_api = Alma_Apis.AlmaRecords(apikey=settings.ALMA_API_KEY[form.cleaned_data['institution']], region='EU', service=__name__)
        status,nb_api_call = alma_api.get_api_remaining()
        if status == "Error" :
            # Pb. de clef où indisponibilité du service
            messages.error(request,"L'API Alma remonte l'erreur suivante :  {}".format(nb_api_call))
            return HttpResponseRedirect("/admin/alma_utils/processupdateitem/add")
        num_ligne = sum(1 for line in request.FILES['file_upload']) - 1
        if (num_ligne*3) > (int(nb_api_call) - 10000) :
            messages.error(request,"Nous ne disposons que de {} appels d'API pour la journée. Votre fichier contient {} lignes. Il faut deux appels par ligne pour traiter le fichier. Merci de diminuer le nombre de lignes à traiter".format(nb_api_call,num_ligne))
            return HttpResponseRedirect("/admin/alma_utils/processupdateitem/add")
        
        user = request.user
        form.save(commit=False)
        obj.num_title_to_processed = num_ligne
        obj.user = user
        obj.save()
        logger.info("Process cree")            
        ExecuteJobThread(obj).start()
        messages.success(request, 'L''analyse a été lancée . Vous recevrez un message sur {} à la fin du traitement'.format( user.email))
        return HttpResponseRedirect("/admin/alma_utils/processupdateitem/")
