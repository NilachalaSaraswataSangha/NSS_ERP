from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import Person

@login_required
def person_list(request):

    persons = Person.objects.filter(
        is_active=True
    ).order_by(
        "first_name"
    )

    context = {
        "persons": persons
    }

    return render(
        request,
        "foundation/person_list.html",
        context
    )

@login_required
def person_detail(request, pk):

    person = get_object_or_404(
        Person,
        pk=pk
    )

    context = {
        "person": person
    }

    return render(
        request,
        "foundation/person_detail.html",
        context
    )