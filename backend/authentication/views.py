from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login


def login_view(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            return redirect("kendra_dashboard")

        return render(
            request,
            "auth/login.html",
            {
                "error": "Invalid Username or Password"
            }
        )

    return render(
        request,
        "auth/login.html"
    )