Chatbot de whatsApp
Sistema de atendimento automatizado via WhatsApp com IA local.

Stack
Backend: Python + FastAPI
Banco de dados: PostgreSQL
IA Local: Ollama + Qwen2.5-coder:3b
Automação: n8n
Deploy: Docker Compose

Estrutura
backend/        → API FastAPI e lógica de negócio
infra/          → Docker Compose e infraestrutura
knowledge_base/ → Documentos para o sistema RAG
tests/          → Testes automatizados
