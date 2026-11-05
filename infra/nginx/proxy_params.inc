proxy_http_version 1.1;
proxy_set_header Connection "";
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_connect_timeout 2s;
proxy_read_timeout 15s;
# Se a conexão com uma réplica falhar, tenta a outra. Só "error/timeout":
# um 503 da aplicação (banco fora) NÃO é mascarado, e POST não é repetido.
proxy_next_upstream error timeout;
proxy_next_upstream_tries 2;
