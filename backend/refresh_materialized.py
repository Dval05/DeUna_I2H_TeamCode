from src.materialized_views import refresh_materialized_views

if __name__ == "__main__":
    ok = refresh_materialized_views(full_refresh=True)
    if ok:
        print("Refresco de vistas materializadas completado.")
    else:
        print("Error refrescando vistas materializadas.")
