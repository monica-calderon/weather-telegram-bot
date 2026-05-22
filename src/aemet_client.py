from __future__ import annotations

import time
from typing import Any

import requests


class AemetClientError(RuntimeError):
    """Raised when AEMET OpenData cannot be queried successfully."""


class AemetClient:
    BASE_URL = "https://opendata.aemet.es/opendata"

    def __init__(self, api_key: str, timeout: int = 20) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()

    def get_municipality_forecast(self, municipio_id: str) -> Any:
        endpoint = (
            f"{self.BASE_URL}/api/prediccion/especifica/municipio/diaria/"
            f"{municipio_id}"
        )
        return self._fetch_aemet_data(endpoint)

    def get_weather_alerts(self, area: str = "72") -> Any:
        endpoint = f"{self.BASE_URL}/api/avisos_cap/ultimoelaborado/area/{area}"
        return self._fetch_aemet_data(endpoint, allow_non_json_data=True)

    def get_current_observations(self, station_id: str | None = None) -> Any:
        if station_id:
            endpoint = (
                f"{self.BASE_URL}/api/observacion/convencional/datos/estacion/"
                f"{station_id}"
            )
        else:
            endpoint = f"{self.BASE_URL}/api/observacion/convencional/todas"
        return self._fetch_aemet_data(endpoint)

    def _fetch_aemet_data(
        self, endpoint_url: str, *, allow_non_json_data: bool = False
    ) -> Any:
        metadata = self._request_json(
            endpoint_url,
            headers={"api_key": self.api_key},
            params={"api_key": self.api_key},
            error_context="AEMET metadata",
        )
        data_url = metadata.get("datos") if isinstance(metadata, dict) else None
        if not data_url:
            descripcion = metadata.get("descripcion") if isinstance(metadata, dict) else None
            raise AemetClientError(
                "AEMET no devolvio la URL 'datos'"
                + (f": {descripcion}" if descripcion else "")
            )

        if allow_non_json_data:
            return self._request_data(data_url, error_context="AEMET datos")
        return self._request_json(data_url, error_context="AEMET datos")

    def _request_json(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        error_context: str,
    ) -> Any:
        response = self._request(
            url, headers=headers, params=params, error_context=error_context
        )
        try:
            return response.json()
        except ValueError as exc:
            raise AemetClientError(
                f"La respuesta de {error_context} no contiene JSON valido"
            ) from exc

    def _request_data(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        error_context: str,
    ) -> Any:
        response = self._request(
            url, headers=headers, params=params, error_context=error_context
        )
        try:
            return response.json()
        except ValueError:
            if response.content.startswith(b"PK"):
                return response.content
            return response.text

    def _request(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        error_context: str,
    ) -> requests.Response:
        last_error: requests.RequestException | None = None
        for attempt in range(3):
            try:
                response = self.session.get(
                    url, headers=headers, params=params, timeout=self.timeout
                )
                if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                    time.sleep(2**attempt)
                    continue
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(2**attempt)
                    continue
                break

        detail = str(last_error) if last_error else "respuesta no disponible"
        if "401" in detail:
            detail += (
                ". AEMET ha rechazado la API key; revisa AEMET_API_KEY en "
                "GitHub Secrets y prueba que no tenga espacios ni comillas."
            )
        if "429" in detail:
            detail += ". AEMET esta limitando temporalmente las peticiones; espera unos minutos."
        raise AemetClientError(f"Error consultando {error_context}: {detail}")
