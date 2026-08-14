#!/usr/bin/env python3
"""
Nuvia WhatsApp ↔ Bigin CRM Synchronization Script
================================================

Sincroniza conversas WhatsApp do Nuvia para o Bigin CRM em tempo real.

Uso:
    python nuvia_bigin_sync.py

Configuração:
    1. Defina as variáveis de ambiente abaixo
    2. Ou edite o arquivo .env (veja exemplo abaixo)

.env Exemplo:
    NUVIA_API_KEY=nuvia_live_xxxxxxxxxxxxx
    NUVIA_ORG_ID=org_xxxxxxxxxxxxx
    BIGIN_API_KEY=xxxxxxxxxxxxx
    BIGIN_SUBDOMAIN=youraccount
    SYNC_INTERVAL=30
    LOG_LEVEL=INFO
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

class Config:
    """Carrega configuração de variáveis de ambiente ou arquivo .env"""

    # API Nuvia
    NUVIA_API_KEY = os.getenv('NUVIA_API_KEY', '')
    NUVIA_ORG_ID = os.getenv('NUVIA_ORG_ID', '')
    NUVIA_BASE_URL = os.getenv('NUVIA_BASE_URL', 'https://app.nuvia.ai/api/v1')

    # API Bigin (Zoho)
    BIGIN_API_KEY = os.getenv('BIGIN_API_KEY', '')
    BIGIN_SUBDOMAIN = os.getenv('BIGIN_SUBDOMAIN', 'youraccount')
    BIGIN_BASE_URL = f'https://www.zohoapis.com/bigin/v1'

    # Sincronização
    SYNC_INTERVAL = int(os.getenv('SYNC_INTERVAL', '30'))  # segundos
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', '5'))  # segundos

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'nuvia_bigin_sync.log')

    # Estado
    STATE_FILE = os.getenv('STATE_FILE', 'sync_state.json')

    @classmethod
    def validate(cls) -> bool:
        """Valida se todas as configurações obrigatórias estão presentes"""
        required = [
            ('NUVIA_API_KEY', cls.NUVIA_API_KEY),
            ('NUVIA_ORG_ID', cls.NUVIA_ORG_ID),
            ('BIGIN_API_KEY', cls.BIGIN_API_KEY),
        ]

        missing = [name for name, value in required if not value]
        if missing:
            print(f"❌ Configuração incompleta. Faltam: {', '.join(missing)}")
            print("\nDefina as variáveis de ambiente:")
            for name, _ in required:
                print(f"  export {name}=seu_valor")
            return False
        return True


# ============================================================================
# LOGGING
# ============================================================================

def setup_logging():
    """Configura logging para arquivo e console"""
    logger = logging.getLogger('nuvia_bigin_sync')
    logger.setLevel(getattr(logging, Config.LOG_LEVEL))

    # Formato
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Handler de arquivo
    try:
        fh = logging.FileHandler(Config.LOG_FILE)
        fh.setLevel(getattr(logging, Config.LOG_LEVEL))
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except Exception as e:
        print(f"⚠️  Aviso: Não foi possível criar arquivo de log: {e}")

    # Handler de console
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(getattr(logging, Config.LOG_LEVEL))
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger

logger = setup_logging()


# ============================================================================
# ESTADO E PERSISTÊNCIA
# ============================================================================

@dataclass
class SyncState:
    """Rastreia o estado de sincronização"""
    last_sync: str = ''  # ISO timestamp
    last_conversation_id: str = ''
    processed_messages: Dict[str, List[str]] = None  # {conv_id: [msg_ids]}
    error_count: int = 0
    sync_count: int = 0

    def __post_init__(self):
        if self.processed_messages is None:
            self.processed_messages = {}

    def save(self, filepath: str = Config.STATE_FILE):
        """Salva estado em JSON"""
        try:
            with open(filepath, 'w') as f:
                json.dump({
                    'last_sync': self.last_sync,
                    'last_conversation_id': self.last_conversation_id,
                    'processed_messages': self.processed_messages,
                    'error_count': self.error_count,
                    'sync_count': self.sync_count,
                }, f, indent=2, default=str)
            logger.debug(f"Estado salvo em {filepath}")
        except Exception as e:
            logger.error(f"Erro ao salvar estado: {e}")

    @staticmethod
    def load(filepath: str = Config.STATE_FILE) -> 'SyncState':
        """Carrega estado de JSON"""
        if not Path(filepath).exists():
            return SyncState()

        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            state = SyncState(**data)
            logger.debug(f"Estado carregado de {filepath}")
            return state
        except Exception as e:
            logger.error(f"Erro ao carregar estado: {e}, usando padrão")
            return SyncState()


# ============================================================================
# NUVIA API
# ============================================================================

class NuviaAPI:
    """Interface para API Nuvia"""

    def __init__(self):
        self.base_url = Config.NUVIA_BASE_URL
        self.headers = {
            'Authorization': f'Bearer {Config.NUVIA_API_KEY}',
            'Content-Type': 'application/json',
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Faz requisição com retry automático"""
        url = f"{self.base_url}{endpoint}"

        for attempt in range(Config.MAX_RETRIES):
            try:
                logger.debug(f"[Nuvia] {method} {url} (tentativa {attempt + 1})")

                response = requests.request(
                    method,
                    url,
                    headers=self.headers,
                    timeout=10,
                    **kwargs
                )
                response.raise_for_status()
                return response.json() if response.text else {}

            except requests.exceptions.RequestException as e:
                logger.warning(f"[Nuvia] Erro na tentativa {attempt + 1}: {e}")
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)
                else:
                    logger.error(f"[Nuvia] Falhou após {Config.MAX_RETRIES} tentativas")
                    return None

    def get_conversations(self, limit: int = 50) -> Optional[List[Dict]]:
        """Lista conversas recentes"""
        result = self._request('GET', f'/organizations/{Config.NUVIA_ORG_ID}/conversations',
                              params={'limit': limit})
        if result and 'conversations' in result:
            logger.info(f"✅ Obtidas {len(result['conversations'])} conversas")
            return result['conversations']
        logger.warning("Nenhuma conversa obtida")
        return []

    def get_conversation_messages(self, conversation_id: str) -> Optional[List[Dict]]:
        """Obtém mensagens de uma conversa específica"""
        result = self._request(
            'GET',
            f'/organizations/{Config.NUVIA_ORG_ID}/conversations/{conversation_id}/messages'
        )
        if result and 'messages' in result:
            return result['messages']
        return []

    def get_contact(self, contact_id: str) -> Optional[Dict]:
        """Obtém detalhes de um contato"""
        result = self._request(
            'GET',
            f'/organizations/{Config.NUVIA_ORG_ID}/contacts/{contact_id}'
        )
        return result

    def search_contacts(self, phone: str) -> Optional[List[Dict]]:
        """Busca contatos por telefone"""
        result = self._request(
            'GET',
            f'/organizations/{Config.NUVIA_ORG_ID}/contacts',
            params={'search': phone}
        )
        if result and 'contacts' in result:
            return result['contacts']
        return []


# ============================================================================
# BIGIN API
# ============================================================================

class BiginAPI:
    """Interface para API Bigin (Zoho)"""

    def __init__(self):
        self.base_url = Config.BIGIN_BASE_URL
        self.headers = {
            'Authorization': f'Zoho-oauthtoken {Config.BIGIN_API_KEY}',
            'Content-Type': 'application/json',
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Faz requisição com retry automático"""
        url = f"{self.base_url}{endpoint}"

        for attempt in range(Config.MAX_RETRIES):
            try:
                logger.debug(f"[Bigin] {method} {url} (tentativa {attempt + 1})")

                response = requests.request(
                    method,
                    url,
                    headers=self.headers,
                    timeout=10,
                    **kwargs
                )
                response.raise_for_status()
                return response.json() if response.text else {}

            except requests.exceptions.RequestException as e:
                logger.warning(f"[Bigin] Erro na tentativa {attempt + 1}: {e}")
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)
                else:
                    logger.error(f"[Bigin] Falhou após {Config.MAX_RETRIES} tentativas")
                    return None

    def find_contact(self, phone: str) -> Optional[str]:
        """Procura contato por telefone, retorna ID ou None"""
        result = self._request('GET', '/Contacts',
                              params={'criteria': f'(Phone:equals:{phone})'})

        if result and 'data' in result and len(result['data']) > 0:
            contact_id = result['data'][0]['id']
            logger.debug(f"Contato encontrado: {contact_id}")
            return contact_id
        return None

    def create_contact(self, data: Dict) -> Optional[str]:
        """Cria novo contato, retorna ID"""
        result = self._request('POST', '/Contacts', json={'data': [data]})

        if result and 'data' in result and len(result['data']) > 0:
            contact_id = result['data'][0]['id']
            logger.info(f"✅ Contato criado: {contact_id}")
            return contact_id

        logger.error(f"Falha ao criar contato: {result}")
        return None

    def update_contact(self, contact_id: str, data: Dict) -> bool:
        """Atualiza contato existente"""
        result = self._request('PUT', f'/Contacts/{contact_id}', json={'data': data})

        if result:
            logger.info(f"✅ Contato atualizado: {contact_id}")
            return True

        logger.error(f"Falha ao atualizar contato {contact_id}: {result}")
        return False

    def add_note(self, contact_id: str, note_text: str) -> Optional[str]:
        """Adiciona nota ao contato"""
        note_data = {
            'Note_Content': note_text,
            'Contact': contact_id
        }
        result = self._request('POST', '/Notes', json={'data': [note_data]})

        if result and 'data' in result and len(result['data']) > 0:
            note_id = result['data'][0]['id']
            logger.debug(f"Nota adicionada: {note_id}")
            return note_id

        logger.error(f"Falha ao adicionar nota: {result}")
        return None


# ============================================================================
# SINCRONIZAÇÃO
# ============================================================================

class NuviaBiginSync:
    """Orquestrador da sincronização"""

    def __init__(self):
        self.nuvia = NuviaAPI()
        self.bigin = BiginAPI()
        self.state = SyncState.load()

    def sync_conversation(self, conversation: Dict) -> bool:
        """Sincroniza uma conversa para Bigin"""
        conv_id = conversation.get('id')
        contact_id = conversation.get('contact_id')

        if not conv_id or not contact_id:
            logger.warning(f"Conversa inválida (faltam campos): {conversation}")
            return False

        try:
            # Obtém dados do contato Nuvia
            contact = self.nuvia.get_contact(contact_id)
            if not contact:
                logger.warning(f"Contato não encontrado na Nuvia: {contact_id}")
                return False

            contact_data = self._prepare_contact_data(contact)
            phone = contact_data.get('Phone')

            if not phone:
                logger.warning(f"Contato sem telefone: {contact_id}")
                return False

            # Procura ou cria contato no Bigin
            bigin_contact_id = self.bigin.find_contact(phone)

            if bigin_contact_id:
                logger.debug(f"Contato existente no Bigin: {bigin_contact_id}")
                self.bigin.update_contact(bigin_contact_id, contact_data)
            else:
                bigin_contact_id = self.bigin.create_contact(contact_data)
                if not bigin_contact_id:
                    return False

            # Obtém e sincroniza mensagens
            messages = self.nuvia.get_conversation_messages(conv_id)
            if messages:
                self._sync_messages(bigin_contact_id, messages, conv_id)

            self.state.sync_count += 1
            return True

        except Exception as e:
            logger.error(f"Erro ao sincronizar conversa {conv_id}: {e}")
            self.state.error_count += 1
            return False

    def _prepare_contact_data(self, contact: Dict) -> Dict:
        """Prepara dados do contato para Bigin"""
        return {
            'First_Name': contact.get('name', 'Cliente'),
            'Phone': contact.get('phone', ''),
            'Email': contact.get('email', ''),
            'Description': f"[WhatsApp] Sincronizado de Nuvia",
        }

    def _sync_messages(self, contact_id: str, messages: List[Dict], conv_id: str):
        """Sincroniza mensagens como notas no Bigin"""
        processed = self.state.processed_messages.get(conv_id, [])

        for msg in messages:
            msg_id = msg.get('id')

            # Evita reprocessar mensagens já sincronizadas
            if msg_id in processed:
                continue

            msg_text = msg.get('content', '')
            sender = msg.get('sender_type', 'unknown')  # 'customer' ou 'agent'
            timestamp = msg.get('timestamp', '')

            note_text = f"[{sender.upper()}] {timestamp}\n{msg_text}"

            if self.bigin.add_note(contact_id, note_text):
                processed.append(msg_id)

        if processed:
            self.state.processed_messages[conv_id] = processed

    def run_once(self) -> bool:
        """Executa um ciclo de sincronização"""
        logger.info("=" * 70)
        logger.info("🔄 Iniciando ciclo de sincronização")

        conversations = self.nuvia.get_conversations()
        if not conversations:
            logger.warning("Nenhuma conversa para sincronizar")
            return False

        synced = 0
        for conv in conversations:
            if self.sync_conversation(conv):
                synced += 1

        self.state.last_sync = datetime.now().isoformat()
        self.state.save()

        logger.info(f"✅ Ciclo completo: {synced}/{len(conversations)} conversas sincronizadas")
        logger.info(f"📊 Total: {self.state.sync_count} sincronizações, {self.state.error_count} erros")
        logger.info("=" * 70)

        return synced > 0

    def run_loop(self):
        """Executa sincronização continuamente"""
        logger.info("🚀 Iniciando loop de sincronização contínua")
        logger.info(f"⏱️  Intervalo: {Config.SYNC_INTERVAL}s")

        try:
            while True:
                self.run_once()
                logger.debug(f"Aguardando {Config.SYNC_INTERVAL}s para próximo ciclo...")
                time.sleep(Config.SYNC_INTERVAL)

        except KeyboardInterrupt:
            logger.info("\n⏹️  Sincronização interrompida pelo usuário")
        except Exception as e:
            logger.error(f"❌ Erro fatal: {e}", exc_info=True)
            sys.exit(1)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Ponto de entrada"""
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                  Nuvia ↔ Bigin CRM Sync Script v1.0                     ║
    ║            Real-time WhatsApp conversation synchronization               ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """)

    # Valida configuração
    if not Config.validate():
        sys.exit(1)

    logger.info("✅ Configuração validada")
    logger.info(f"📍 Log: {Config.LOG_FILE}")

    # Inicia sincronização
    sync = NuviaBiginSync()

    if len(sys.argv) > 1 and sys.argv[1] == 'once':
        # Modo one-shot
        logger.info("📍 Modo: Sincronização única")
        sync.run_once()
    else:
        # Modo loop contínuo
        logger.info("📍 Modo: Loop contínuo")
        sync.run_loop()


if __name__ == '__main__':
    main()
