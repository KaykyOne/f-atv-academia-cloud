"""Serviço `publicador` (Grupo 2): lê a outbox e entrega eventos ao serviço de notificações.

Garantia: entrega AO MENOS UMA VEZ. Se o consumidor estiver fora do ar, o evento
continua `pendente` e é tentado de novo com espera exponencial; após
MAX_TENTATIVAS vira `falho` (o administrador pode reprocessar). Como uma
reentrega é possível, o consumidor descarta eventos repetidos pelo `evento_id`.
"""
import json
import logging
import os
import time
import urllib.error
import urllib.request
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from app.config import database_url
from app.models import eventos, agora, make_engine

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s publicador %(message)s')
HEARTBEAT = '/tmp/publicador.heartbeat'


def enviar_http(url):
    def enviar(ev):
        corpo = json.dumps({'evento_id': ev['id'], 'tipo': ev['tipo'], 'dados': json.loads(ev['payload'])})
        req = urllib.request.Request(url, data=corpo.encode(), method='POST',
                                     headers={'Content-Type': 'application/json', 'Idempotency-Key': ev['id']})
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.load(r).get('status', 'ok')
    return enviar


def processar_lote(engine, enviar, limite=20, max_tentativas=8):
    """Processa eventos vencidos. Retorna (entregues, falhas)."""
    entregues = falhas = 0
    with engine.begin() as c:
        # SKIP LOCKED: vários publicadores poderiam rodar sem pegar o mesmo evento.
        lote = c.execute(select(eventos)
                         .where(eventos.c.status == 'pendente', eventos.c.proxima_tentativa <= agora())
                         .order_by(eventos.c.criado_em).limit(limite)
                         .with_for_update(skip_locked=True)).mappings().all()
        for ev in lote:
            tentativas = ev['tentativas'] + 1
            try:
                resultado = enviar(ev)
                c.execute(update(eventos).where(eventos.c.id == ev['id']).values(
                    status='entregue', tentativas=tentativas, entregue_em=agora(), ultimo_erro=None))
                entregues += 1
                logging.info('evento=%s tipo=%s entregue resultado=%s tentativa=%s',
                             ev['id'], ev['tipo'], resultado, tentativas)
            except (OSError, ValueError) as e:
                status = 'falho' if tentativas >= max_tentativas else 'pendente'
                espera = min(2 ** tentativas, 300)
                c.execute(update(eventos).where(eventos.c.id == ev['id']).values(
                    status=status, tentativas=tentativas, ultimo_erro=f'{type(e).__name__}: {e}'[:300],
                    proxima_tentativa=agora() + timedelta(seconds=espera)))
                falhas += 1
                logging.warning('evento=%s falha tentativa=%s status=%s proxima_em=%ss erro=%s',
                                ev['id'], tentativas, status, espera, type(e).__name__)
    return entregues, falhas


def main():
    engine = make_engine(database_url())
    enviar = enviar_http(os.getenv('NOTIF_URL', 'http://notificacoes:8001') + '/events')
    intervalo = float(os.getenv('PUBLICADOR_INTERVALO', '2'))
    max_tent = int(os.getenv('PUBLICADOR_MAX_TENTATIVAS', '8'))
    logging.info('iniciado intervalo=%ss max_tentativas=%s', intervalo, max_tent)
    while True:
        try:
            processar_lote(engine, enviar, max_tentativas=max_tent)
            with open(HEARTBEAT, 'w') as f:  # usado pelo healthcheck do container
                f.write(str(time.time()))
        except SQLAlchemyError as e:
            logging.error('banco indisponivel type=%s', type(e).__name__)
        time.sleep(intervalo)


if __name__ == '__main__':
    main()
