from utils.api_client import fetch_news_from_api
from utils.ai_utils import summarize_article
from .models import db, NewsArticle
from flask import current_app

def get_latest_news(category=None):
    """
    Fluxo de notícias com Cache Inteligente para evitar limites da IA.
    """
    # 1. Busca notícias na API (Google News)
    raw_news = fetch_news_from_api(category)
    
    if not raw_news:
        return []

    processed_news = []
    
    # 2. Processar com Cache e IA
    # Queremos devolver mais notícias para o portal (ex.: "Tudo"), mas sem ficar lento/caro:
    # - até 20 artigos no máximo
    # - IA apenas nos primeiros N (resto usa snippet como fallback)
    max_items = 20
    max_ai_items = 8

    for idx, article in enumerate(raw_news[:max_items]):
        # Verificar se este artigo já existe na nossa base de dados (cache)
        existing_article = NewsArticle.query.filter_by(url=article['url']).first()
        
        if existing_article and existing_article.ai_summary:
            # Usar o resumo que já temos guardado
            article['summary'] = existing_article.ai_summary
            print(f"CACHE: Usando resumo guardado para: {article['title'][:30]}...")
        else:
            if idx < max_ai_items:
                # Se não temos em cache, pedimos ao Gemini
                print(f"IA: Gerando novo resumo para: {article['title'][:30]}...")
                article['summary'] = summarize_article(article['title'], article.get('content'))
            else:
                # Para o resto, devolvemos algo rápido (snippet) e evitamos chamadas de IA
                article['summary'] = article.get('content') or "Sem descrição disponível."
            
            # Guardar na base de dados para a próxima vez (Cache Global)
            try:
                if not existing_article:
                    new_cache = NewsArticle(
                        title=article['title'],
                        content=article['content'],
                        url=article['url'],
                        category=article.get('category'),
                        source=article.get('source'),
                        image_url=article.get('image_url'),
                        published_at=article.get('published_at'),
                        ai_summary=article['summary'] if idx < max_ai_items else None
                    )
                    db.session.add(new_cache)
                else:
                    if idx < max_ai_items:
                        existing_article.ai_summary = article['summary']
                
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Erro ao guardar em cache: {e}")

        processed_news.append(article)
        
    return processed_news


def get_latest_news_grouped(categories, per_category=8):
    """
    Devolve notícias agrupadas por categoria para a vista "Tudo".
    Mantém performance: IA só para os primeiros itens de cada categoria.
    """
    sections = []

    for cat in categories:
        raw_news = fetch_news_from_api(cat)
        if not raw_news:
            continue

        processed = []
        max_ai_items = 3

        for idx, article in enumerate(raw_news[:per_category]):
            existing_article = NewsArticle.query.filter_by(url=article['url']).first()

            if existing_article and existing_article.ai_summary:
                article['summary'] = existing_article.ai_summary
            else:
                if idx < max_ai_items:
                    article['summary'] = summarize_article(article['title'], article.get('content'))
                else:
                    article['summary'] = article.get('content') or "Sem descrição disponível."

                try:
                    if not existing_article:
                        new_cache = NewsArticle(
                            title=article['title'],
                            content=article['content'],
                            url=article['url'],
                            category=article.get('category'),
                            source=article.get('source'),
                            image_url=article.get('image_url'),
                            published_at=article.get('published_at'),
                            ai_summary=article['summary'] if idx < max_ai_items else None
                        )
                        db.session.add(new_cache)
                    else:
                        if idx < max_ai_items:
                            existing_article.ai_summary = article['summary']
                    db.session.commit()
                except Exception:
                    db.session.rollback()

            processed.append(article)

        sections.append({"category": cat, "items": processed})

    return sections
