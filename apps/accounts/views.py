from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import datetime, timedelta
from apps.financeiro.models import Lancamento
from .forms import PerfilForm
from .models import LogAcesso

@login_required
def perfil_view(request):
    if request.method == 'POST':
        form = PerfilForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil atualizado com sucesso.')
            return redirect('accounts:perfil')
    else:
        form = PerfilForm(instance=request.user)
    
    # --- FILTROS ---
    hoje_str = timezone.localdate().strftime('%Y-%m-%d')
    data_inicial = request.GET.get('data_inicial', hoje_str)
    data_final = request.GET.get('data_final', hoje_str)
    
    # Pega múltiplos valores para 'tipo'. Se nenhum for enviado, assume 'todos'
    tipos_filtro = request.GET.getlist('tipo')
    if not tipos_filtro:
        tipos_filtro = ['todos']

    # Converte as datas (com fuso)
    tz = timezone.get_current_timezone()
    try:
        dt_inicial = timezone.make_aware(datetime.strptime(data_inicial, '%Y-%m-%d'), tz)
        dt_final = timezone.make_aware(
            datetime.strptime(data_final, '%Y-%m-%d').replace(hour=23, minute=59, second=59), tz
        )
    except ValueError:
        dt_final = timezone.now()
        dt_inicial = dt_final - timedelta(days=30)

    logs = []

    # Se 'todos' estiver selecionado, mostramos tudo
    mostrar_todos = 'todos' in tipos_filtro

    # 1. Logs de Lançamentos
    if mostrar_todos or any(t in tipos_filtro for t in ['inclusao', 'edicao', 'exclusao']):
        historicos = Lancamento.history.filter(
            history_user=request.user,
            history_date__range=(dt_inicial, dt_final)
        ).order_by('-history_date')[:50]
        
        for h in historicos:
            if h.history_type == '+': acao = 'inclusao'
            elif h.history_type == '~': acao = 'edicao'
            elif h.history_type == '-': acao = 'exclusao'
            else: continue

            # Se não for 'todos' e essa ação específica não estiver na lista, ignora
            if not mostrar_todos and acao not in tipos_filtro:
                continue

            if acao == 'inclusao': cor = 'text-[#15803D]'
            elif acao == 'edicao': cor = 'text-[#2563EB]'
            elif acao == 'exclusao': cor = 'text-[#B91C1C]'

            logs.append({
                'data_obj': h.history_date,
                'acao': acao.capitalize(),
                'detalhe': f"Lançamento #{h.id} — {h.descricao}",
                'cor': cor
            })

    # 2. Logs de Acesso
    if mostrar_todos or any(t in tipos_filtro for t in ['login', 'logout']):
        acessos = LogAcesso.objects.filter(
            usuario=request.user,
            data__range=(dt_inicial, dt_final)
        ).order_by('-data')[:50]

        for a in acessos:
            if not mostrar_todos and a.acao not in tipos_filtro:
                continue
            
            logs.append({
                'data_obj': a.data,
                'acao': a.acao.capitalize(),
                'detalhe': 'Entrou no sistema' if a.acao == 'login' else 'Saiu do sistema',
                'cor': 'text-[#6B7B78]'
            })

    # Ordena tudo junto pela data
    logs.sort(key=lambda x: x['data_obj'], reverse=True)
    
    for log in logs:
        log['data'] = timezone.localtime(log['data_obj']).strftime('%d/%m/%Y %H:%M')

    return render(request, 'accounts/perfil.html', {
        'form': form,
        'logs': logs[:50],
        'modo_edicao': request.GET.get('edit') == '1',
        'data_inicial': data_inicial,
        'data_final': data_final,
        'tipos_filtro': tipos_filtro, # Passamos a lista
    })