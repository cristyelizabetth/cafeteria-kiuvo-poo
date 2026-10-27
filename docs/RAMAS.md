# Cómo subir el proyecto entre las cinco (ramas y Pull Requests)

Una forma de subir esta versión al repositorio para que **cada una tenga commits propios**. Los nombres de persona son ejemplos; repártanlo como prefieran.

## Reparto sugerido

| Persona | Rama | Archivos |
|---|---|---|
| 1 | `poo-modelos` | `modelos/` (todas las clases del dominio) |
| 2 | `poo-base-datos` | `base_datos.py`, carpeta `dao/`, `datos_iniciales.py`, `docs/BASE_DE_DATOS.md`, `docs/CAMBIOS_NORMALIZACION.md`, `docs/diagrama_base_datos.*` |
| 3 | `poo-seguridad` | `seguridad.py`, `servicios.py`, `config.py`, `.gitignore`, `requirements.txt` |
| 4 | `poo-rutas` | `app.py`, `contenedor.py`, `sesion.py`, `rutas/`, `pruebas/` |
| 5 | `poo-diseno` | `templates/`, `static/`, `README.md`, `docs/CLASES.md`, `docs/diagrama_clases*`, `docs/RAMAS.md`, `docs/CAMBIOS_RUBRICA.md`, `docs/GUIA_DEFENSA.md` |

Cada una necesita saber explicar lo que subió: los archivos de `docs/` ayudan.

## Pasos para cada persona

```bash
# 1. Traer lo último de main
git checkout main
git pull

# 2. Crear su rama
git checkout -b poo-modelos

# 3. Copiar SOLO sus archivos desde el zip a la carpeta del repo
#    (los archivos viejos que ya no se usan, bórrenlos en una de las ramas)

# 4. Guardar y subir
git add modelos/
git commit -m "Agregar clases del dominio con enfoque POO"
git push -u origin poo-modelos
```

5. En GitHub: **Compare & pull request** → describir el cambio → otra compañera lo revisa → **Merge**.

## Orden recomendado para unir

El sitio funciona completo cuando están las cinco ramas. Para evitar conflictos, unan los Pull Requests en este orden:

1. `poo-modelos`
2. `poo-base-datos`
3. `poo-seguridad`
4. `poo-rutas`
5. `poo-diseno`

Después de unir todo, en `main`:

```bash
git pull
pip install -r requirements.txt
python -m unittest discover pruebas
python app.py
```

## Importante

- **No suban** la carpeta `instancia/` (tiene la base de datos y la clave secreta). Ya está en `.gitignore`.
- Si en `main` todavía están los archivos de la versión anterior (`modelos.py`, `db.py`, etc.), bórrenlos en un commit propio (`git rm modelos.py db.py`) para que no choquen con la carpeta `modelos/`.
- Cada una debe hacer el commit **desde su propia cuenta de GitHub** para que aparezca a su nombre. Revisen con `git config user.name` y `git config user.email`.
