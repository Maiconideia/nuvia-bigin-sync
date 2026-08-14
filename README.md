# 🚀 Nuvia WhatsApp → Bigin CRM Sync

Sincroniza conversas WhatsApp da **Nuvia** para o **Bigin CRM** em tempo real (24/7).

## ⚡ Deploy Rápido no Railway

### Passo 1: Criar Repositório no GitHub

1. Vá para https://github.com/new
2. Crie um repositório chamado `nuvia-bigin-sync`
3. Clone para seu PC:
```bash
git clone https://github.com/seu_usuario/nuvia-bigin-sync.git
cd nuvia-bigin-sync
```

### Passo 2: Copie os Arquivos

Coloque estes arquivos na pasta:
- `nuvia_bigin_sync.py`
- `.env` (com suas credenciais)
- `requirements.txt`
- `Procfile`
- `README.md` (este arquivo)

### Passo 3: Commit e Push

```bash
git add .
git commit -m "Initial commit: Nuvia-Bigin sync setup"
git push origin main
```

### Passo 4: Deploy no Railway

1. Vá para https://railway.app/
2. Clique em **"New Project"**
3. Selecione **"Deploy from GitHub"**
4. Autorize Railway a acessar seu GitHub
5. Selecione o repositório `nuvia-bigin-sync`
6. Railway faz deploy automático ✅

### Passo 5: Configurar Variáveis de Ambiente

No dashboard do Railway:
1. Vá para **"Variables"**
2. Adicione as variáveis (copie do seu `.env`):
   ```
   NUVIA_API_KEY=seu_valor
   NUVIA_ORG_ID=seu_valor
   NUVIA_BASE_URL=https://api.nuvia.ai
   BIGIN_API_KEY=seu_valor
   BIGIN_REFRESH_TOKEN=seu_valor
   BIGIN_SUBDOMAIN=bigin
   SYNC_INTERVAL=30
   ```

## 📊 Monitorar

No Railway:
- Veja **Logs** em tempo real
- Verifique **Status** do deployment
- Reinicie se necessário

## 💰 Custo

- **Grátis** até 500 horas/mês (~$5 se exceder)
- Sem cartão de crédito necessário inicialmente

## 📝 Logs

Os logs aparecem em:
- Railway Dashboard → Logs
- Arquivo local: `nuvia_bigin_sync.log`

---

**Pronto!** Seu sync roda 24/7 automaticamente no Railway! 🎉
