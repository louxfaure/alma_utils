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
    ordering = ('-start_date',)
    search_fields = ('file_upload',)
    fieldsets = (
        (None, {
            'fields': ('institution','base','file_upload' ),
            'description': ""
        }),
    )
    form = UploadFileForm

    # Ajoute un bloc dédié au messade utilisateur
    def render_change_form(self, request, context, *args, **kwargs):
        # here we define a custom template
        self.change_form_template = 'alma_utils/message_aide.html'
        
        return super(UpdateItemProcesss, self).render_change_form(request,
            context, *args, **kwargs)
            
    # Empêche le message standart d'enregistrement d'un modèle à l'execution d'un traitement
    def message_user(self, request, message, level=messages.INFO, extra_tags='',
                 fail_silently=False):
        pass


    def save_model(self, request, obj, form, change):
        user = request.user
        form.save(commit=False)
        obj.num_title_to_processed = sum(1 for line in request.FILES['file_upload']) - 1
        obj.user = user
        obj.save()
        logger.info("Process cree")            
        ExecuteJobThread(obj).start()
        messages.success(request, 'L''analyse a été lancée . Vous recevrez un message sur {} à la fin du traitement'.format( user.email))
        pass
