from django.core.management.base import BaseCommand

from apps.financeiro.models import Centro, ContaFinanceira, SubCentro

SUBCENTROS = {
    "CTSUL": ["Administrativo", "Ecografia", "Internados", "Raio X", "Tomografia"],
    "RSUL": ["Administrativo", "Internados", "Ressonância"],
}

CONTAS = [
    ("101", "R", "Convênio"),
    ("102", "R", "Cartões"),
    ("201", "D", "Glosa"),
]


class Command(BaseCommand):
    help = "Cria centros, sub-centros e contas iniciais (pode rodar mais de uma vez)."

    def handle(self, *args, **options):
        for nome_centro, subs in SUBCENTROS.items():
            centro, _ = Centro.objects.get_or_create(nome=nome_centro)
            for nome_sub in subs:
                SubCentro.objects.get_or_create(centro=centro, nome=nome_sub)

        for codigo, tipo, nome in CONTAS:
            ContaFinanceira.objects.get_or_create(
                codigo=codigo, defaults={"tipo": tipo, "nome": nome}
            )

        self.stdout.write(self.style.SUCCESS("Dados iniciais criados."))