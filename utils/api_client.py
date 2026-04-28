import requests
from flask import current_app

def fetch_news_from_api(category=None):
    """
    Consome a SerpApi (Google News) de forma robusta.
    Focado nas categorias que a API consegue processar com alta relevância.
    """
    api_key = current_app.config.get('NEWS_API_KEY')
    base_url = "https://serpapi.com/search"
    
    # Se for uma categoria das preferências, usamos como busca direta
    # Caso contrário, pesquisamos notícias gerais de Portugal
    query = category if category and category.lower() != 'none' else "notícias portugal"
    
    params = {
        "engine": "google_news",
        "q": query,
        "gl": "pt", 
        "hl": "pt",
        "api_key": api_key
    }

    try:
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        articles = data.get("news_results", [])
        formatted_news = []

        # Aumentado para 20 notícias para um portal rico em conteúdo
        for art in articles[:20]:
            # Suporte a grupos de histórias
            if "stories" in art:
                art = art["stories"][0]

            formatted_news.append({
                "title": art.get("title", "Sem Título"),
                "content": art.get("snippet") or "Sem descrição disponível.",
                "url": art.get("link", "#"),
                "category": category if category else "Geral",
                "image_url": art.get("thumbnail") or "https://via.placeholder.com/600x400/000/FFCC00?text=NewsAI",
                "source": art.get("source", {}).get("name", "Google News"),
                "published_at": art.get("date", "Recentemente")
            })

        return formatted_news

    except Exception as e:
        print(f"Erro na API (SerpApi): {e}")
        return []
