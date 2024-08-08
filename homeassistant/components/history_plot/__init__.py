"""The History Plot integration."""

from __future__ import annotations

from collections import defaultdict, namedtuple
from datetime import datetime as dt, timedelta
from http import HTTPStatus
from io import BytesIO
import logging
import re
import string
from typing import cast
from urllib.parse import unquote

from aiohttp import web
from matplotlib.axes import Axes
from matplotlib.dates import AutoDateLocator, ConciseDateFormatter
from matplotlib.figure import Figure

from homeassistant.components.http import HomeAssistantView
from homeassistant.components.recorder import get_instance, history
from homeassistant.components.recorder.util import session_scope
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, valid_entity_id
from homeassistant.helpers import entity_registry
import homeassistant.util.dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
_ONE_DAY = timedelta(days=1)

FigureParams = namedtuple("FigureParams", ["width", "height", "dpi", "background"])


class ParameterParseError(Exception):
    """Exception raised when parsing of an input failed."""


class PlotView(HomeAssistantView):
    """Base class for all views of this component."""

    def parse_int(self, value: str | None, name: str) -> int:
        """Parse the value into a int."""
        try:
            if value is None:
                return None
            return int(value)
        except BaseException as exc:
            _LOGGER.warning("Error parsing int name %s: %s", name, value, exc_info=exc)
            raise ParameterParseError(f"Error parsing {name}") from None

    def parse_float(self, value: str | None, name: str) -> float:
        """Parse the value into a float."""
        try:
            if value is None:
                return None
            return float(value)
        except BaseException as exc:
            _LOGGER.warning(
                "Error parsing float name %s: %s", name, value, exc_info=exc
            )
            raise ParameterParseError(f"Error parsing {name}") from None

    def parse_bool(self, value: str | None, name: str) -> bool:
        """Parse the value into a bool."""
        try:
            if value is None:
                return None
            if value.lower() in ["true", "t", "y"]:
                return True
            if value.lower() in ["false", "f", "n"]:
                return False
            return self.parse_int(value, name) != 0
        except BaseException as exc:
            _LOGGER.warning("Error parsing bool name %s: %s", name, value, exc_info=exc)
            raise ParameterParseError(f"Error parsing {name}") from None

    def parse_int_array(
        self, value: str, name: str, length: int | None = None
    ) -> list[int]:
        """Parse the value into a list of strings."""
        result = [self.parse_int(x, name) for x in value.split(",")]
        if length is not None and len(result) != length:
            raise ParameterParseError(f"Error parsing {name}") from None
        return result

    def read_figure_params(self, request: web.Request) -> FigureParams:
        """Read all parameters related to the figure from the request."""
        image_width, image_height = self.parse_int_array(
            request.query.get("size", "640,480"), "size", 2
        )
        dpi = self.parse_int(request.query.get("dpi", "100"), "dpi")
        background = unquote(request.query.get("background", "white"))
        if all(c in string.hexdigits for c in background) and (
            len(background) == 6 or len(background) == 8
        ):
            background = "#" + background
        return FigureParams(image_width, image_height, dpi, background)

    def create_figure(self, figure_params: FigureParams) -> tuple[Figure, Axes]:
        """Create a new matplotlib Figure."""
        figsize = (figure_params.width / 100.0, figure_params.height / 100.0)
        fig = Figure(
            figsize=figsize, dpi=figure_params.dpi, facecolor=figure_params.background
        )
        ax = fig.subplots()
        ax.set_facecolor(figure_params.background)
        return fig, ax

    def create_png_response(self, fig: Figure) -> web.Response:
        """Create a new Response object containing the Figure as png."""
        buf = BytesIO()
        fig.savefig(buf, format="png")

        return web.Response(body=buf.getvalue(), content_type="image/png")

    def read_entitiy_params(
        self, request: web.Request
    ) -> list[tuple[str, dict[str, str]]]:
        """Read all entities and their parameters from the request."""
        entities = request.query.get("entities")
        if not entities:
            raise ParameterParseError("No entities given")
        hass = request.app["hass"]
        entity_list = []
        entities = entities.lower().split(",")
        for idx, entity_raw in enumerate(entities):
            entity = unquote(entity_raw)
            settings = {}
            if "[" in entity and entity[-1] == "]":
                entity, settings_str = entity.split("[", 1)
                for entry in settings_str[:-1].split(";"):
                    if ":" not in entry:
                        raise ParameterParseError(
                            f"Entity Parameter without value: {entity}"
                        )
                    k, v = entry.split(":", 1)
                    settings[k] = v
            for k, v in request.query.items():
                if k.startswith(entity + "_"):
                    settings[k[len(entity + 1) :]] = unquote(v)
                if k.startswith("e" + str(idx + 1)):
                    settings[k[len("e" + str(idx + 1))]] = unquote(v)

            if not hass.states.get(entity) and not valid_entity_id(entity):
                raise ParameterParseError("Invalid entity_id " + str(entity))

            entity_list.append((entity, settings))
        return entity_list

    async def get(self, request: web.Request, *args, **kwargs) -> web.Response:
        """Perform the get request."""
        try:
            return await self.do_get(request, *args, **kwargs)
        except ParameterParseError as exc:
            return self.json_message(exc.args[0], HTTPStatus.BAD_REQUEST)


class BaseEntityHistoryPlotView(PlotView):
    """Generates a plot of the history data of one or more entities."""

    url = "/api/plot/history"
    name = "api:plot:history"
    extra_urls = ["/api/plot/history/{datetime}"]

    async def do_get(
        self, request: web.Request, datetime: str | None = None
    ) -> web.Response:
        """Read data and generate the image."""
        _LOGGER.warning("EntityHistoryPlotView.get")
        datetime_ = None
        query = request.query

        if datetime and (datetime_ := dt_util.parse_datetime(datetime)) is None:
            raise ParameterParseError("Invalid datetime")

        now = dt_util.utcnow()
        if datetime_:
            start_time = dt_util.as_utc(datetime_)
        else:
            start_time = now - _ONE_DAY

        if start_time > now:
            return self.json([])

        if end_time_str := query.get("end_time"):
            if end_time := dt_util.parse_datetime(end_time_str):
                end_time = dt_util.as_utc(end_time)
            else:
                return self.json_message("Invalid end_time", HTTPStatus.BAD_REQUEST)
        elif duration_str := query.get("duration"):
            if duration := dt_util.parse_duration(duration_str):
                end_time = start_time + duration
            else:
                return self.json_message("Invalid duration", HTTPStatus.BAD_REQUEST)
        else:
            end_time = start_time + _ONE_DAY

        ymin = self.parse_float(query.get("ymin", None), "ymin")
        ymax = self.parse_float(query.get("ymax", None), "ymax")
        grid = query.get("grid", "")
        title = query.get("title", None)
        if title:
            title = unquote(title)
        xlabel = query.get("xlabel", None)
        if xlabel:
            xlabel = unquote(xlabel)
        ylabel = query.get("ylabel", None)
        if ylabel:
            ylabel = unquote(ylabel)

        entities = self.read_entitiy_params(request)
        figure_params = self.read_figure_params(request)
        hass = request.app["hass"]

        return cast(
            web.Response,
            await get_instance(hass).async_add_executor_job(
                self._create_image,
                hass,
                start_time,
                end_time,
                entities,
                figure_params,
                ymin,
                ymax,
                grid,
                title,
                xlabel,
                ylabel,
            ),
        )

    def _create_image(
        self,
        hass: HomeAssistant,
        start_time: dt,
        end_time: dt,
        entities: list[tuple[str, dict[str, str]]],
        figure_params: FigureParams,
        # image_width: int,
        # image_height: int,
        # background: str,
        ymin: float | None,
        ymax: float | None,
        grid: str,
        title: str | None,
        xlabel: str | None,
        ylabel: str | None,
    ):
        def to_float(s: str) -> float:
            try:
                return float(s)
            except (ValueError, TypeError, OverflowError):
                return None

        def smooth(
            scalars: list[float], weight: float
        ) -> list[float]:  # Weight between 0 and 1
            last = scalars[0]  # First value in the plot (first timestep)
            smoothed = []
            for point in scalars:
                smoothed_val = (
                    last * weight + (1 - weight) * point
                )  # Calculate smoothed value
                smoothed.append(smoothed_val)  # Save it
                last = smoothed_val  # Anchor the last smoothed value

            return smoothed

        with session_scope(hass=hass, read_only=True) as session:
            state_history = history.get_significant_states_with_session(
                hass,
                session,
                start_time,
                end_time,
                [entity_info[0] for entity_info in entities],
                None,
            )

        fig, ax = self.create_figure(figure_params)

        for entity_id, entity_settings in entities:
            entity_states = state_history[entity_id]

            if self.parse_bool(
                entity_settings.get("exclude_unknown", None),
                entity_id + "_exclude_unkown",
            ):
                data = {
                    es.last_changed: to_float(es.state)
                    for es in entity_states
                    if es.state and to_float(es.state) is not None
                }
            else:
                data = {
                    es.last_changed: to_float(es.state)
                    for es in entity_states
                    if es.state
                }
            times, values = zip(*data.items(), strict=False)
            smoothing = self.parse_float(
                entity_settings.get("smooth", None), entity_id + "_smooth"
            )
            if smoothing:
                values = smooth(values, smoothing)
            fmt = entity_settings.get("fmt", "")
            lw = self.parse_int(entity_settings.get("lw", "1"), entity_id + "_lw")
            ax.plot(times, values, fmt, lw=lw)
            if self.parse_bool(entity_settings.get("fill", None), entity_id + "_fill"):
                fill_settings = {
                    "color": entity_settings.get("fill_color", None),
                    "alpha": entity_settings.get("fill_alpha", None),
                    "hatch": entity_settings.get("fill_hatch", None),
                }
                fill_settings = {
                    k: v for k, v in fill_settings.items() if v is not None
                }
                ax.fill_between(times, values, min(values), **fill_settings)
            ax.set_ybound(ymin, ymax)
            locator = AutoDateLocator()
            formatter = ConciseDateFormatter(locator)
            ax.xaxis.set_major_formatter(formatter)
            ax.xaxis.set_major_locator(locator)

        if "x" in grid and "y" in grid:
            ax.grid(axis="both")
        elif "x" in grid:
            ax.grid(axis="x")
        elif "y" in grid:
            ax.grid(axis="y")

        if title:
            ax.set_title(title)
        if xlabel:
            ax.set_xlabel(xlabel)
        if ylabel:
            ax.set_ylabel(ylabel)

        return self.create_png_response(fig)


class EntityHistoryBoxPlotView(BaseEntityHistoryPlotView):
    """Generates a box plot of the history data of one or more entities."""

    url = "/api/plot/box_history/"
    name = "api:plot:box_history"
    extra_urls = ["/api/plot/box_history/{datetime}"]


class EntityHistoryPlotView(PlotView):
    """Generates a plot of the history data of one or more entities."""

    url = "/api/plot/history"
    name = "api:plot:history"
    extra_urls = ["/api/plot/history/{datetime}"]

    async def do_get(
        self, request: web.Request, datetime: str | None = None
    ) -> web.Response:
        """Read data and generate the image."""
        _LOGGER.warning("EntityHistoryPlotView.get")
        datetime_ = None
        query = request.query

        if datetime and (datetime_ := dt_util.parse_datetime(datetime)) is None:
            raise ParameterParseError("Invalid datetime")

        now = dt_util.utcnow()
        if datetime_:
            start_time = dt_util.as_utc(datetime_)
        else:
            start_time = now - _ONE_DAY

        if start_time > now:
            return self.json([])

        if end_time_str := query.get("end_time"):
            if end_time := dt_util.parse_datetime(end_time_str):
                end_time = dt_util.as_utc(end_time)
            else:
                return self.json_message("Invalid end_time", HTTPStatus.BAD_REQUEST)
        elif duration_str := query.get("duration"):
            if duration := dt_util.parse_duration(duration_str):
                end_time = start_time + duration
            else:
                return self.json_message("Invalid duration", HTTPStatus.BAD_REQUEST)
        else:
            end_time = start_time + _ONE_DAY

        ymin = self.parse_float(query.get("ymin", None), "ymin")
        ymax = self.parse_float(query.get("ymax", None), "ymax")
        grid = query.get("grid", "")
        title = query.get("title", None)
        if title:
            title = unquote(title)
        xlabel = query.get("xlabel", None)
        if xlabel:
            xlabel = unquote(xlabel)
        ylabel = query.get("ylabel", None)
        if ylabel:
            ylabel = unquote(ylabel)

        entities = self.read_entitiy_params(request)
        figure_params = self.read_figure_params(request)
        hass = request.app["hass"]

        return cast(
            web.Response,
            await get_instance(hass).async_add_executor_job(
                self._create_image,
                hass,
                start_time,
                end_time,
                entities,
                figure_params,
                ymin,
                ymax,
                grid,
                title,
                xlabel,
                ylabel,
            ),
        )

    def _create_image(
        self,
        hass: HomeAssistant,
        start_time: dt,
        end_time: dt,
        entities: list[tuple[str, dict[str, str]]],
        figure_params: FigureParams,
        # image_width: int,
        # image_height: int,
        # background: str,
        ymin: float | None,
        ymax: float | None,
        grid: str,
        title: str | None,
        xlabel: str | None,
        ylabel: str | None,
    ):
        def to_float(s: str) -> float:
            try:
                return float(s)
            except (ValueError, TypeError, OverflowError):
                return None

        def smooth(
            scalars: list[float], weight: float
        ) -> list[float]:  # Weight between 0 and 1
            last = scalars[0]  # First value in the plot (first timestep)
            smoothed = []
            for point in scalars:
                smoothed_val = (
                    last * weight + (1 - weight) * point
                )  # Calculate smoothed value
                smoothed.append(smoothed_val)  # Save it
                last = smoothed_val  # Anchor the last smoothed value

            return smoothed

        with session_scope(hass=hass, read_only=True) as session:
            state_history = history.get_significant_states_with_session(
                hass,
                session,
                start_time,
                end_time,
                [entity_info[0] for entity_info in entities],
                None,
            )

        fig, ax = self.create_figure(figure_params)

        for entity_id, entity_settings in entities:
            entity_states = state_history[entity_id]

            if self.parse_bool(
                entity_settings.get("exclude_unknown", None),
                entity_id + "_exclude_unkown",
            ):
                data = {
                    es.last_changed: to_float(es.state)
                    for es in entity_states
                    if es.state and to_float(es.state) is not None
                }
            else:
                data = {
                    es.last_changed: to_float(es.state)
                    for es in entity_states
                    if es.state
                }
            times, values = zip(*data.items(), strict=False)
            smoothing = self.parse_float(
                entity_settings.get("smooth", None), entity_id + "_smooth"
            )
            if smoothing:
                values = smooth(values, smoothing)
            fmt = entity_settings.get("fmt", "")
            lw = self.parse_int(entity_settings.get("lw", "1"), entity_id + "_lw")
            ax.plot(times, values, fmt, lw=lw)
            if self.parse_bool(entity_settings.get("fill", None), entity_id + "_fill"):
                fill_settings = {
                    "color": entity_settings.get("fill_color", None),
                    "alpha": entity_settings.get("fill_alpha", None),
                    "hatch": entity_settings.get("fill_hatch", None),
                }
                fill_settings = {
                    k: v for k, v in fill_settings.items() if v is not None
                }
                ax.fill_between(times, values, min(values), **fill_settings)
            ax.set_ybound(ymin, ymax)
            locator = AutoDateLocator()
            formatter = ConciseDateFormatter(locator)
            ax.xaxis.set_major_formatter(formatter)
            ax.xaxis.set_major_locator(locator)

        if "x" in grid and "y" in grid:
            ax.grid(axis="both")
        elif "x" in grid:
            ax.grid(axis="x")
        elif "y" in grid:
            ax.grid(axis="y")

        if title:
            ax.set_title(title)
        if xlabel:
            ax.set_xlabel(xlabel)
        if ylabel:
            ax.set_ylabel(ylabel)

        return self.create_png_response(fig)


class PiePlotView(PlotView):
    """Presents a Pie view of values of entities."""

    url = "/api/plot/pie"
    name = "api:plot:pie"

    series_regex = re.compile("series(\\d+)\\_(.+)", re.IGNORECASE)

    async def do_get(self, request: web.Request) -> web.Response:
        entities = self.read_entitiy_params(request)
        figure_params = self.read_figure_params(request)
        title = request.query.get("title", None)
        if title:
            title = unquote(title)

        series_params = defaultdict(dict)
        for k, v in request.query.items():
            if match := self.series_regex.search(k):
                i = self.parse_int(match.group(1), "Series value in " + k)
                setting = match.group(2)
                series_params[i][setting] = unquote(v)

        hass = request.app["hass"]

        return cast(
            web.Response,
            await get_instance(hass).async_add_executor_job(
                self._create_image, hass, entities, figure_params, series_params, title
            ),
        )

    def _create_image(
        self,
        hass: HomeAssistant,
        entities: list[tuple[str, dict[str, str]]],
        figure_params: FigureParams,
        series_params: dict[str, dict[str, str]],
        title: str | None,
    ):
        er = entity_registry.async_get(hass)

        def to_float(s: str) -> float:
            try:
                return float(s)
            except (ValueError, TypeError, OverflowError):
                return None

        series = defaultdict(list)
        for e in entities:
            series_idx = self.parse_int(e[1].get("series", "0"), e[0] + "_series")
            series[series_idx].append(e)

        fig, ax = self.create_figure(figure_params)

        for series_idx, series_entities in sorted(series.items()):
            values = [to_float(hass.states.get(e[0]).state) for e in series_entities]
            explode = [
                self.parse_float(e[1].get("explode", "0"), e[0] + "_explode")
                for e in series_entities
            ]
            colors = [e[1].get("color", None) for e in series_entities]
            labels = [
                e[1].get("label", er.async_get(e[0]).name) for e in series_entities
            ]

            radius = self.parse_float(
                series_params[series_idx].get("radius", "1"),
                f"series{series_idx}_radius",
            )
            labeldistance = self.parse_float(
                series_params[series_idx].get("labeldistance", "1.1"),
                f"series{series_idx}_labeldistance",
            )
            autopct = series_params[series_idx].get("autopct", None)
            pctdistance = self.parse_float(
                series_params[series_idx].get("pctdistance", "1.1"),
                f"series{series_idx}_pctdistance",
            )
            shadow = self.parse_bool(
                series_params[series_idx].get("shadow", "False"),
                f"series{series_idx}_shadow",
            )
            hatch = series_params[series_idx].get("hatch", None)
            font_family = series_params[series_idx].get("font_family", None)
            font_color = series_params[series_idx].get("font_color", None)
            font_size = self.parse_float(
                series_params[series_idx].get("font_size", None),
                f"series{series_idx}_font_size",
            )
            font_weight = self.parse_int(
                series_params[series_idx].get("font_weight", None),
                f"series{series_idx}_font_weight",
            )
            wedge_width = self.parse_float(
                series_params[series_idx].get("width", "1"), f"series{series_idx}_width"
            )
            edgecolor = series_params[series_idx].get("edgecolor", None)
            textprops = {}
            if font_family is not None:
                textprops["fontfamily"] = font_family
            if font_color is not None:
                textprops["color"] = font_color
            if font_size is not None:
                textprops["fontsize"] = font_size
            if font_weight is not None:
                textprops["fontweight"] = font_weight
            wedgeprops = {"width": wedge_width}
            if edgecolor is not None:
                wedgeprops["edgecolor"] = edgecolor

            _LOGGER.warning(
                f"Drawing series {series_idx} with {[e[0] for e in series_entities]} ({values}); radius: {radius}; width: {wedge_width}; autopct: {autopct}"
            )

            ax.pie(
                values,
                labels=labels,
                labeldistance=labeldistance,
                autopct=autopct,
                pctdistance=pctdistance,
                explode=explode,
                colors=colors,
                radius=radius,
                hatch=hatch,
                textprops=textprops,
                wedgeprops=wedgeprops,
                shadow=shadow,
            )

        if title:
            ax.set_title(title)
        return self.create_png_response(fig)


class HistoryPlotView(HomeAssistantView):
    url = "/api/history/plot"
    name = "api:history:view-plot"
    extra_urls = ["/api/history/plot/{datetime}"]

    def parse_int(self, value: str | None, name: str) -> int:
        """Parse the value into a string."""
        try:
            if value is None:
                return None
            return int(value)
        except BaseException:
            raise ParameterParseError(f"Error parsing {name}") from None

    def parse_float(self, value: str | None, name: str) -> float:
        """Parse the value into a string."""
        try:
            if value is None:
                return None
            return float(value)
        except BaseException:
            raise ParameterParseError(f"Error parsing {name}") from None

    def parse_int_array(
        self, value: str, name: str, length: int | None = None
    ) -> list[int]:
        """Parse the value into a list of strings."""
        result = [self.parse_int(x, name) for x in value.split(",")]
        if length is not None and len(result) != length:
            raise ParameterParseError(f"Error parsing {name}") from None
        return result

    async def get(
        self, request: web.Request, datetime: str | None = None
    ) -> web.Response:
        _LOGGER.warning("HistoryPlotView.get")

        datetime_ = None
        query = request.query

        if datetime and (datetime_ := dt_util.parse_datetime(datetime)) is None:
            return self.json_message("Invalid datetime", HTTPStatus.BAD_REQUEST)

        if not (entity_ids_str := query.get("filter_entity_id")) or not (
            entity_ids := entity_ids_str.strip().lower().split(",")
        ):
            return self.json_message(
                "filter_entity_id is missing", HTTPStatus.BAD_REQUEST
            )

        try:
            image_width, image_height = self.parse_int_array(
                query.get("size", "640,480"), "Size", 2
            )
            background = unquote(query.get("background", "white"))
            ymin = self.parse_float(query.get("ymin", None), "ymin")
            ymax = self.parse_float(query.get("ymax", None), "ymax")
            grid = query.get("grid", "")
            title = query.get("title", None)
            if title:
                title = unquote(title)
            xlabel = query.get("xlabel", None)
            if xlabel:
                xlabel = unquote(xlabel)
            ylabel = query.get("ylabel", None)
            if ylabel:
                ylabel = unquote(ylabel)
            linefmt = query.get("linefmt", "").split(",")

            hass = request.app["hass"]

            for entity_id in entity_ids:
                if not hass.states.get(entity_id) and not valid_entity_id(entity_id):
                    return self.json_message(
                        "Invalid filter_entity_id", HTTPStatus.BAD_REQUEST
                    )

            now = dt_util.utcnow()
            if datetime_:
                start_time = dt_util.as_utc(datetime_)
            else:
                start_time = now - _ONE_DAY

            if start_time > now:
                return self.json([])

            if end_time_str := query.get("end_time"):
                if end_time := dt_util.parse_datetime(end_time_str):
                    end_time = dt_util.as_utc(end_time)
                else:
                    return self.json_message("Invalid end_time", HTTPStatus.BAD_REQUEST)
            else:
                end_time = start_time + _ONE_DAY

            # await get_instance(hass).async_add_executor_job(
            #    self._create_image,
            #    hass,
            #    start_time,
            #    end_time,
            #    entity_ids
            # )

            # fig = Figure()
            # ax = fig.subplots()
            # ax.plot([1, 2])
            ## Save it to a temporary buffer.
            # buf = BytesIO()
            # fig.savefig(buf, format="png")

            # return web.Response(body=buf.getvalue(), content_type='image/png')
            return cast(
                web.Response,
                await get_instance(hass).async_add_executor_job(
                    self._create_image,
                    hass,
                    start_time,
                    end_time,
                    entity_ids,
                    image_width,
                    image_height,
                    background,
                    ymin,
                    ymax,
                    grid,
                    title,
                    xlabel,
                    ylabel,
                    linefmt,
                ),
            )
        except ParameterParseError as exc:
            return self.json_message(exc.args[0], HTTPStatus.BAD_REQUEST)

    def _create_image(
        self,
        hass: HomeAssistant,
        start_time: dt,
        end_time: dt,
        entity_ids: list[str],
        image_width: int,
        image_height: int,
        background: str,
        ymin: float | None,
        ymax: float | None,
        grid: str,
        title: str | None,
        xlabel: str | None,
        ylabel: str | None,
        linefmt: list[str],
    ):
        def to_float(s: str) -> float:
            try:
                return float(s)
            except (ValueError, TypeError, OverflowError):
                return None

        def smooth(
            scalars: list[float], weight: float
        ) -> list[float]:  # Weight between 0 and 1
            last = scalars[0]  # First value in the plot (first timestep)
            smoothed = []
            for point in scalars:
                smoothed_val = (
                    last * weight + (1 - weight) * point
                )  # Calculate smoothed value
                smoothed.append(smoothed_val)  # Save it
                last = smoothed_val  # Anchor the last smoothed value

            return smoothed

        with session_scope(hass=hass, read_only=True) as session:
            state_history = history.get_significant_states_with_session(
                hass, session, start_time, end_time, entity_ids, None
            )

            _LOGGER.warning(f"States: {state_history}")

        figsize = (image_width / 100.0, image_height / 100.0)
        fig = Figure(figsize=figsize, facecolor=background)
        ax = fig.subplots()
        ax.set_facecolor(background)

        for idx, entity_id in enumerate(entity_ids):
            # for entity_id, entity_states in state_history.items():
            entity_states = state_history[entity_id]
            times = [x.last_changed for x in entity_states if x.state]
            values = [to_float(x.state) for x in entity_states]
            _LOGGER.warning(f"{entity_id} __ {times} __ {values}")
            ax.plot(times, values)
            ax.set_ybound(ymin, ymax)
            locator = AutoDateLocator()
            formatter = ConciseDateFormatter(locator)
            ax.xaxis.set_major_formatter(formatter)
            ax.xaxis.set_major_locator(locator)
            if idx < len(linefmt):
                linefmt[idx]

        if "x" in grid and "y" in grid:
            ax.grid(axis="both")
        elif "x" in grid:
            ax.grid(axis="x")
        elif "y" in grid:
            ax.grid(axis="y")

        if title:
            ax.set_title(title)
        if xlabel:
            ax.set_xlabel(xlabel)
        if ylabel:
            ax.set_ylabel(ylabel)

        # ax.plot([1, 2])
        # Save it to a temporary buffer.
        buf = BytesIO()
        fig.savefig(buf, format="png")

        return web.Response(body=buf.getvalue(), content_type="image/png")


# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
# PLATFORMS: list[Platform] = [Platform.LIGHT]


async def async_setup(hass: HomeAssistant, config) -> bool:
    hass.http.register_view(HistoryPlotView())
    hass.http.register_view(EntityHistoryPlotView())
    hass.http.register_view(PiePlotView())
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up History Plot from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    # TODO 1. Create API instance
    # TODO 2. Validate the API connection (and authentication)
    # TODO 3. Store an API object for your platforms to access
    # hass.data[DOMAIN][entry.entry_id] = MyApi(...)

    # await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
    #    hass.data[DOMAIN].pop(entry.entry_id)

    return True
