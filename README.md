# Job Searcher

Armé este proyecto para seguir búsquedas de empleo en ingeniería y análisis de datos sin tener que revisar cada portal por separado. Junta ofertas de distintas fuentes, detecta duplicados y permite ordenar las oportunidades según su relevancia.

Además de mostrar vacantes, guarda un historial para ver qué roles, habilidades y empresas aparecen con más frecuencia.

## Qué hace

- Recolecta y normaliza ofertas de portales, feeds públicos y páginas de empleo de empresas.
- Guarda las ofertas y sus cambios en una base local.
- Muestra un tablero para filtrar oportunidades, revisar postulaciones y explorar tendencias del mercado.
- Puede evaluar ofertas con Claude y enviar alertas por Telegram si se configuran esas integraciones.

## Tecnologías

Backend en **Python** con **FastAPI**, **SQLAlchemy** y **SQLite**. Frontend en **React** con **Vite**. Las búsquedas y fuentes se ajustan desde los archivos de `config/`.

## Uso local

Con Python 3.12 y Node.js instalados, en Windows ejecutá `setup_v2.bat` una vez y después `run_v2.bat`. El tablero queda en [localhost:5173](http://localhost:5173).

Las claves para Claude, Telegram y otras fuentes son opcionales y se configuran en `.env` a partir de `.env.example`. La base de datos local y las credenciales no están incluidas en el repositorio.
