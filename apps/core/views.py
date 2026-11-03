# --- CALENDÁRIO ---
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import TarefaCalendario, RegraCalendario
import json
from datetime import datetime
from django.shortcuts import render

@login_required
def home(request):
    return render(request, "core/home.html")

@login_required
def api_tarefas_calendario(request):
    tarefas = TarefaCalendario.objects.filter(criado_por=request.user)
    lista = [{'id': t.id, 'title': t.titulo, 'start': t.data.strftime('%Y-%m-%d'), 'done': t.done} for t in tarefas]
    return JsonResponse(lista, safe=False)

@login_required
@require_POST
def salvar_tarefa_calendario(request):
    try:
        dados = json.loads(request.body)
        titulo = dados.get('titulo', '').strip().upper()
        data_str = dados.get('data')
        if titulo and data_str:
            data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
            TarefaCalendario.objects.create(titulo=titulo, data=data_obj, criado_por=request.user)
            return JsonResponse({'status': 'sucesso'})
    except Exception as e:
        return JsonResponse({'status': 'erro', 'msg': str(e)}, status=400)
    return JsonResponse({'status': 'erro'}, status=400)

@login_required
@require_POST
def editar_tarefa_calendario(request, pk):
    try:
        tarefa = TarefaCalendario.objects.get(pk=pk, criado_por=request.user)
        dados = json.loads(request.body)
        if 'titulo' in dados:
            tarefa.titulo = dados['titulo'].strip().upper()
        if 'done' in dados:
            tarefa.done = dados['done']
        tarefa.save()
        return JsonResponse({'status': 'sucesso'})
    except Exception as e:
        return JsonResponse({'status': 'erro', 'msg': str(e)}, status=400)

@login_required
@require_POST
def excluir_tarefa_calendario(request, pk):
    try:
        tarefa = TarefaCalendario.objects.get(pk=pk, criado_por=request.user)
        tarefa.delete()
        return JsonResponse({'status': 'sucesso'})
    except Exception as e:
        return JsonResponse({'status': 'erro', 'msg': str(e)}, status=400)

@login_required
def api_regras_calendario(request):
    regras = RegraCalendario.objects.filter(criado_por=request.user)
    lista = [{'id': r.id, 'titulo': r.titulo, 'tipo': r.tipo, 'dias': r.dias} for r in regras]
    return JsonResponse(lista, safe=False)

@login_required
@require_POST
def salvar_regra_calendario(request):
    try:
        dados = json.loads(request.body)
        RegraCalendario.objects.create(
            titulo=dados.get('titulo'),
            tipo=dados.get('tipo'),
            dias=dados.get('dias'),
            criado_por=request.user
        )
        return JsonResponse({'status': 'sucesso'})
    except Exception as e:
        return JsonResponse({'status': 'erro', 'msg': str(e)}, status=400)

@login_required
@require_POST
def excluir_regra_calendario(request, pk):
    try:
        regra = RegraCalendario.objects.get(pk=pk, criado_por=request.user)
        regra.delete()
        return JsonResponse({'status': 'sucesso'})
    except Exception as e:
        return JsonResponse({'status': 'erro', 'msg': str(e)}, status=400)