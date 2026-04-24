from django.shortcuts import render


def apteka911(request):
    return render(request, 'base.html', context={
        'page_title': 'Аптека 911',
        'content': 'pharmacy.html',
    })