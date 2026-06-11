from django.shortcuts import render


def kendra_dashboard(request):

    return render(
        request,
        "dashboard/kendra_dashboard.html"
    )