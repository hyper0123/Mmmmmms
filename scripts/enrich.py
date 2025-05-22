# scripts/enrich.py
import os
import json
import requests
import re

# Clave TMDB desde variable de entorno
api_key = os.environ['TMDB_API_KEY']
base_search = 'https://api.themoviedb.org/3/search/movie'
base_movie  = 'https://api.themoviedb.org/3/movie'

# Helper para obtener detalles e imágenes

def fetch_details(movie_id, lang='es-MX'):
    det = requests.get(f"{base_movie}/{movie_id}", params={
        'api_key': api_key,
        'language': lang
    }).json()
    imgs = requests.get(f"{base_movie}/{movie_id}/images", params={
        'api_key': api_key
    }).json()
    return det, imgs


def main():
    # Cargar JSON base
    with open('playlist.json', encoding='utf-8') as f:
        data = json.load(f)

    enriched = []
    for item in data:
        sample = item['samples'][0]
        orig_title = sample['name']
        orig_year  = sample.get('anio','').strip()

        # 1) buscar en inglés con año
        params = {
            'api_key': api_key,
            'language': 'en-US',
            'query': orig_title
        }
        if orig_year:
            params['year'] = orig_year
        results = requests.get(base_search, params=params).json().get('results', [])

        # 2) si no hay, buscar sin año
        if not results:
            params.pop('year', None)
            results = requests.get(base_search, params=params).json().get('results', [])

        if results:
            movie = results[0]
            tmdb_year = movie.get('release_date','')[:4]
            # corregir año ±1
            if tmdb_year and orig_year and abs(int(tmdb_year) - int(orig_year)) == 1:
                corrected_year = tmdb_year
            else:
                corrected_year = orig_year or tmdb_year

            # detalles en español
            det, imgs = fetch_details(movie['id'], lang='es-MX')
            title_es   = det.get('title') or orig_title
            genres     = [g['name'] for g in det.get('genres', [])]
            overview   = det.get('overview','').strip()
            release_date = det.get('release_date','')
            final_year = release_date[:4] if release_date else corrected_year
            runtime    = det.get('runtime', 0)

            poster     = f"https://image.tmdb.org/t/p/original{det.get('poster_path','')}"   if det.get('poster_path')   else ''
            backdrop   = f"https://image.tmdb.org/t/p/original{det.get('backdrop_path','')}" if det.get('backdrop_path') else ''
            logos      = imgs.get('logos', [])
            logo_url   = f"https://image.tmdb.org/t/p/original{logos[0]['file_path']}" if logos else ''

            top_name = genres[0] if genres else ''
            sample_name = title_es
            sample_year = final_year
            description = overview
            duration    = f"{runtime} min"
            all_genres  = genres
        else:
            # no encontrado
            top_name     = 'Variado'
            sample_name  = orig_title
            sample_year  = orig_year
            description  = ''
            poster       = ''
            backdrop     = ''
            logo_url     = ''
            duration     = ''
            all_genres   = []

        enriched.append({
            'name': top_name,
            'samples': [{
                'name': sample_name,
                'url': sample['url'],
                'icono': poster,
                'iconoHorizontal': backdrop,
                'iconpng': logo_url,
                'type': 'PELICULA',
                'descripcion': description,
                'anio': sample_year,
                'genero': all_genres,
                'duracion': duration
            }]
        })

    # Volcar JSON final completo
    with open('playlist.enriched.json', 'w', encoding='utf-8') as f:
        json.dump(enriched, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    main()
