from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class PerfilForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['nome_completo', 'email', 'telefone', 'cargo', 'foto']
        widgets = {
            'nome_completo': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500'}),
            'email': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500'}),
            'telefone': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500'}),
            'cargo': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500'}),
        }