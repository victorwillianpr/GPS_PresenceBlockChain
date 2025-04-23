# GPS_PresenceBlockChain

## Estrutura de Arquivos

- blockchain_server.py: servidor FastAPI e implementação da blockchain.
- attendance.html: interface web que captura localização e interage com o servidor.
- requirements.txt: lista de dependências Python.
- blockchain.json: arquivo JSON que mantém o histórico de blocos.

-----------------------------------------------------------------------------------

## Execução

- Crie um ambiente virtual e ative-o:
    python -m venv venv
    venv\Scripts\activate      # Windows

- Instale as dependências:
    pip install -r requirements.txt

- Inicie o servidor (em um terminal):
    uvicorn blockchain_server:app --reload

- Configurar área (em um terminal Git Bash):
    curl -X POST http://localhost:8000/attendance/configure \
        -H "Content-Type: application/json" \
        -d '{"latitude":-3.1190,"longitude":-60.0217,"tolerance_m":50}'

- Abra attendance.html no navegador.

- Permita o uso de localização no navegador quando solicitado.

- Verifique a localização clicando em Verificar Localização.

- Registre presença clicando em Registrar Presença (habilitado se dentro da área).

- Bloco minerado exibido em blockchain.json
