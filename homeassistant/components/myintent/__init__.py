"""The My Intent integration."""
from __future__ import annotations

import datetime
import enum
import logging
from typing import Any

# from homeassistant.config_entries import ConfigEntry
# from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Activate Alexa component."""
    intent.async_register(hass, WeatherIntentHandler())
    return True


class WeatherDataTypes(enum.Flag):
    """Possible types of data points that make up the weather"""

    NONE = 0
    CONDITION = 1
    TEMPERATURE = 2
    SHORT = 3
    WIND = 12
    WIND_SPEED = 4
    WIND_BEARING = 8
    MEDIUM = 15
    NORMAL = 15
    HUMIDITY = 16
    PRESSURE = 32
    LONG = 63
    FULL = 63


state_translation = {
    "clear-night": "eine klare nacht",
    "cloudy": "bewölkt",
    "exceptional": "außergewöhnliches wetter",
    "fog": "neblig",
    "hail": "hagel",
    "lightning": "gewitter",
    "lightning-rainy": "regen und gewitter",
    "partlycloudy": "teilweise bewölkt",
    "pouring": "starker regen",
    "rainy": "regen",
    "snowy": "schneefall",
    "snowy-rainy": "schneeregen",
    "sunny": "sonnig",
    "windy": "windig",
    "windy-variant": "windig und bewölkt",
}


class WeatherIntentHandler(intent.IntentHandler):
    """Respond to a weather update request."""

    def __init__(self):
        """Initialize the script intent handler."""
        self.intent_type = "WeatherReport"

    def get_wind_speed(self, wind_speed: Any) -> tuple[int, float, str]:
        if wind_speed is None:
            return None
        wind_speed = float(wind_speed)
        if wind_speed < 2:
            wind_str = 0
            wind_str_desc = "windstille"
        elif wind_speed < 10:
            wind_str = 1
            wind_str_desc = "leichter zug"
        elif wind_speed < 20:
            wind_str = 2
            wind_str_desc = "leichte brise"
        elif wind_speed < 29:
            wind_str = 3
            wind_str_desc = "schwache brise"
        elif wind_speed < 39:
            wind_str = 4
            wind_str_desc = "mäßige brise"
        elif wind_speed < 49:
            wind_str = 5
            wind_str_desc = "frische brise"
        elif wind_speed < 58:
            wind_str = 6
            wind_str_desc = "starker wind"
        elif wind_speed < 67:
            wind_str = 7
            wind_str_desc = "starker bis stürmischer wind"
        elif wind_speed < 76:
            wind_str = 8
            wind_str_desc = "stürmischer wind"
        elif wind_speed < 85:
            wind_str = 9
            wind_str_desc = "sturm"
        elif wind_speed < 94:
            wind_str = 10
            wind_str_desc = "sturm bis schwerer sturm"
        elif wind_speed < 103:
            wind_str = 11
            wind_str_desc = "schwerer sturm"
        else:
            wind_str = 12
            wind_str_desc = "orkan"
        return (wind_str, wind_speed, wind_str_desc)

    def get_bearing(self, direction: Any) -> tuple[float, str, str]:
        if direction is None:
            return None
        directions = [
            ("N", "nord"),
            ("NNO", "nord nordost"),
            ("NO", "nordost"),
            ("ONO", "ost nordost"),
            ("O", "ost"),
            ("OSO", "ost südost"),
            ("SO", "südost"),
            ("SSO", "süd südost"),
            ("S", "süd"),
            ("SSW", "süd südwest"),
            ("SW", "südwest"),
            ("WSW", "west südwest"),
            ("W", "west"),
            ("WNW", "west nordwest"),
            ("NW", "nordwest"),
            ("NNW", "nord nordwest"),
            ("N", "nord"),
        ]
        section = int((float(direction) + 11.25) / 22.5)
        direction_name = directions[section]
        return (float(direction), direction_name[0], direction_name[1])

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        """Handle the intent."""
        response = intent_obj.create_response()
        hass = intent_obj.hass
        weather_state = hass.states.get("weather.forecast_home")
        if weather_state is None:
            response.async_set_speech("Wetter ist nicht verfügbar")
            response.async_set_card("Wetter ist nicht verfügbar")
            return response
        slots = intent_obj.slots
        when = slots.get("when", {"value": None})["value"]
        what = slots.get("what", {"value": "normal"})["value"]
        if when in [None, "", "heute", "today"]:
            weather = weather_state.attributes
            condition = str(weather_state.state)
            reply = "es ist"
        #            in_future = False
        else:
            #            in_future = True
            if when in ["morgen", "tomorrow"]:
                target_date = datetime.date.today() + datetime.timedelta(1)
            else:
                target_date = datetime.date.today() + datetime.timedelta(int(when))
            valid_entries = [
                w
                for w in weather_state.attributes["forecast"]
                if datetime.datetime.fromisoformat(w["datetime"]).date() == target_date
            ]
            valid_entries.sort(
                key=lambda w: datetime.datetime.fromisoformat(w["datetime"])
            )
            weather = valid_entries[0]
            condition = weather["condition"]
            reply = "es wird"
        condition = state_translation.get(condition, condition)
        temperature = float(weather["temperature"])
        humidity = float(weather["humidity"])
        pressure = float(weather["pressure"])
        wind_speed = self.get_wind_speed(weather["wind_speed"])
        wind_bearing = self.get_bearing(weather["wind_bearing"])

        what_available = WeatherDataTypes.NONE
        if condition is not None:
            what_available |= WeatherDataTypes.CONDITION
        if temperature is not None:
            what_available |= WeatherDataTypes.TEMPERATURE
        if humidity is not None:
            what_available |= WeatherDataTypes.HUMIDITY
        if pressure is not None:
            what_available |= WeatherDataTypes.PRESSURE
        if wind_speed is not None:
            what_available |= WeatherDataTypes.WIND_SPEED
        if wind_bearing is not None:
            what_available |= WeatherDataTypes.WIND_BEARING

        _LOGGER.warning("What_available: %s", what_available)
        _LOGGER.warning("What: %s", what)

        what = next(
            (
                type[1]
                for type in WeatherDataTypes.__members__.items()
                if type[0].startswith(what.upper())
            ),
            None,
        )
        _LOGGER.warning("What: %s", what)
        if what is None or what is WeatherDataTypes.NONE:
            response.async_set_speech("ich kenne dieses wetter nicht")
            response.async_set_card("Wetter", "Unbekannter Wettertyp")
            return response
        what &= what_available
        if what is WeatherDataTypes.NONE:
            response.async_set_speech("dafür habe ich keine daten")
            response.async_set_card("Wetter", "Keine Daten")
            return response

        reply = ""
        if what & WeatherDataTypes.CONDITION:
            reply = condition
        if what & WeatherDataTypes.TEMPERATURE:
            if len(reply) == 0:
                reply = str(temperature) + " grad"
            else:
                reply += " bei " + str(temperature) + " grad"
        if what & WeatherDataTypes.WIND_SPEED:
            if len(reply) == 0:
                reply = wind_speed[2]
            else:
                reply += " und " + wind_speed[2]
        if what & WeatherDataTypes.WIND_BEARING:
            if len(reply) == 0:
                reply = "wind aus " + wind_bearing[2]
            elif what & WeatherDataTypes.WIND_SPEED:
                reply += " aus " + wind_bearing[2]
            else:
                reply += " und wind aus " + wind_bearing[2]
        if what & WeatherDataTypes.HUMIDITY:
            if len(reply) == 0:
                reply = "luftfeuchtigkeit von " + humidity + " prozent"
            else:
                reply += "mit einer luftfeuchtigkeit von " + humidity + " prozent"
        if what & WeatherDataTypes.PRESSURE:
            reply += " der luftdruck ist " + pressure

        response.async_set_speech(reply)
        response.async_set_card("Wetter", reply)
        return response
