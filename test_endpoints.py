#!/usr/bin/env python3
"""
Script para testar variações de endpoints da API Nuvia
Identifica qual endpoint retorna dados ao invés de 404
"""

import os
import requests
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

NUVIA_API_KEY = os.getenv('NUVIA_API_KEY')
NUVIA_ORG_ID = os.getenv('NUVIA_ORG_ID')
NUVIA_BASE_URL = os.getenv('NUVIA_BASE_URL', 'https://api.nuvia.ai')

# Headers com autenticação
headers = {
    'X-API-Key': NUVIA_API_KEY,
    'Content-Type': 'application/json'
}

# Lista de endpoints para testar
endpoints_to_test = [
    f'{NUVIA_BASE_URL}/conversations?limit=10',
    f'{NUVIA_BASE_URL}/organizations/{NUVIA_ORG_ID}/conversations?limit=10',
    f'{NUVIA_BASE_URL}/chats?limit=10',
    f'{NUVIA_BASE_URL}/organizations/{NUVIA_ORG_ID}/chats?limit=10',
    f'{NUVIA_BASE_URL}/messages?limit=10',
    f'{NUVIA_BASE_URL}/organizations/{NUVIA_ORG_ID}/messages?limit=10',
    f'{NUVIA_BASE_URL}/v1/conversations?limit=10',
    f'{NUVIA_BASE_URL}/v1/organizations/{NUVIA_ORG_ID}/conversations?limit=10',
]

print("=" * 80)
print("TESTANDO ENDPOINTS DA API NUVIA")
print("=" * 80)
print(f"Base URL: {NUVIA_BASE_URL}")
print(f"Org ID: {NUVIA_ORG_ID}")
print(f"API Key (primeiros 20 caracteres): {NUVIA_API_KEY[:20]}...")
print("=" * 80)
print()

success_count = 0

for endpoint in endpoints_to_test:
    print(f"Testando: {endpoint}")
    try:
        response = requests.get(endpoint, headers=headers, timeout=10)
        print(f"  Status Code: {response.status_code}")

        if response.status_code == 200:
            print(f"  ✓ SUCESSO! Endpoint retorna dados")
            print(f"  Response length: {len(response.text)} caracteres")
            try:
                data = response.json()
                if isinstance(data, dict):
                    print(f"  Chaves na resposta: {list(data.keys())}")
                elif isinstance(data, list):
                    print(f"  Tipo: Lista com {len(data)} itens")
            except:
                print(f"  Response (primeiros 500 caracteres): {response.text[:500]}")
            success_count += 1
        elif response.status_code == 401:
            print(f"  ✗ Erro de autenticação (401)")
        elif response.status_code == 404:
            print(f"  ✗ Endpoint não encontrado (404)")
        else:
            print(f"  ✗ Erro {response.status_code}")
            try:
                print(f"  Response: {response.json()}")
            except:
                print(f"  Response: {response.text[:200]}")
    except requests.exceptions.Timeout:
        print(f"  ✗ Timeout (10s)")
    except requests.exceptions.ConnectionError as e:
        print(f"  ✗ Erro de conexão: {str(e)[:100]}")
    except Exception as e:
        print(f"  ✗ Erro: {str(e)[:100]}")

    print()

print("=" * 80)
print(f"RESUMO: {success_count} endpoint(s) funcionando")
print("=" * 80)

if success_count == 0:
    print("\n⚠️  Nenhum endpoint retornou dados com sucesso")
    print("Verificar:")
    print("  1. API Key válida?")
    print("  2. Organization ID correto?")
    print("  3. API da Nuvia está online?")
else:
    print(f"\n✓ Encontrados {success_count} endpoint(s) funcional(is)")
    print("Use o endpoint que retornou sucesso no arquivo nuvia_bigin_sync.py")
