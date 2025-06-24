from django.apps import AppConfig


class MainConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "main"

    def ready(self):
        from .utils.fuel_loader import load_fuel_stations
        load_fuel_stations()