from src.main import normalize_forecast


def test_normalize_forecast_includes_max_periods_and_sky_status():
    forecast = [
        {
            "prediccion": {
                "dia": [
                    {
                        "fecha": "2026-05-22",
                        "temperatura": {
                            "maxima": 28,
                            "minima": 14,
                            "dato": [
                                {"value": 14, "hora": 6},
                                {"value": 24, "hora": 12},
                                {"value": 27, "hora": 18},
                            ],
                        },
                        "probPrecipitacion": [
                            {"value": 20, "periodo": "0006"},
                            {"value": 70, "periodo": "1218"},
                        ],
                        "viento": [
                            {"velocidad": 10, "periodo": "0006"},
                            {"velocidad": 55, "periodo": "1824"},
                        ],
                        "estadoCielo": [
                            {"value": "12", "periodo": "0006", "descripcion": "Poco nuboso"}
                        ],
                    }
                ]
            }
        }
    ]

    normalized = normalize_forecast(forecast, "Alcala")

    assert normalized["rain_probability"] == 70
    assert normalized["rain_period"] == "entre 12:00 y 18:00"
    assert normalized["wind_kmh"] == 55
    assert normalized["wind_period"] == "entre 18:00 y 24:00"
    assert normalized["sky_status"] == "Poco nuboso"
    assert normalized["hourly_temperatures"] == [
        {"periodo": "06", "value": 14},
        {"periodo": "12", "value": 24},
        {"periodo": "18", "value": 27},
    ]
