from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
from .service.services import FogoCruzadoService
from .models import Occurrence 




def health_view(request):
    return HttpResponse("Health Check OK CARAJOOOOO")


def occurrences_view(request):
    try:
        FogoCruzadoService.update_occurrences()

        # Fetch the updated occurrences from the database
        occurrences = Occurrence.objects.all().values()
        occurrences_list = list(occurrences)

        return JsonResponse({'occurrences': occurrences_list}, safe=False, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def health_view(request):
    return HttpResponse("Health Check OK")