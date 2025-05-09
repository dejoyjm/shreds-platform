from django.urls import path
from .views import RegisterView, hello_user

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('hello/', hello_user, name='hello_user'),
]
