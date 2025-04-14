from django.shortcuts import render, redirect
from django.views import View
from django.urls import reverse_lazy
from .forms import UserRegistrationForm, UserProfileForm

# accounts/views.py
class RegisterCreateView(View):
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('login')

    def get(self, request):
        return render(request, self.template_name, {
            'user_form':    UserRegistrationForm(),
            'profile_form': UserProfileForm()
        })

    def post(self, request):
        user_form    = UserRegistrationForm(request.POST)
        profile_form = UserProfileForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()           
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()
            return redirect(self.success_url)

        return render(request, self.template_name, {
            'user_form':    user_form,
            'profile_form': profile_form
        })
    